import json
import re
import threading
import typing
import logging
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from tkinter import messagebox

from ops_toolkit.todolist.models import map_status_to_int
from ops_toolkit.todolist.models import TodolistTaskModel
from ops_toolkit.todolist.models import DBManager
from ops_toolkit.todolist.schedule import ScheduleManager
from ops_toolkit.todolist.ui_create_window import TodoCreateWindow
from ops_toolkit.todolist.ui_floating_window import FloatingWindow
from ops_toolkit.todolist.ui_floating_window import TaskItem
from ops_toolkit.todolist.ui_summary import SummaryWindow
from ops_toolkit.tools import DaemonTimer
from ops_toolkit.tools import toolkit_notify_callback

if typing.TYPE_CHECKING:
    from ops_toolkit.app import App

logger = logging.getLogger("ops_toolkit.todolist.main")


class TodoManager:
    """待办事项管理器"""

    def __init__(self, app: "App"):
        self.app: "App" = app
        self.db_manager: DBManager = DBManager(self.app.config.data_dir)

        self.floating_window: FloatingWindow = FloatingWindow(self.app, self)
        self.reminder_manager: ReminderManager = ReminderManager(self)
        self.workdir_manager: WorkdirManager = WorkdirManager(self)
        self.scheduler = ScheduleManager(self)
        self.summary: SummaryWindow = SummaryWindow(self.app, self)

        self.after_id_window_update = None

    def show_summary_window(self):
        """显示默认窗口"""
        self.summary.show()

    def show_create_window(self):
        """显示创建窗口"""
        TodoCreateWindow(self)

    def show_display_window(self):
        """显示展示窗口"""
        self.floating_window.show()

    def update_window(self):
        """更新窗口"""

        def _update():
            try:
                self.floating_window.load_tasks()
                self.summary.load_tasks()
                logger.debug("Todolist 窗口列表已经更新")
                self.timer_window_update = None
            except Exception as _e:
                logger.error(f"Todolist 窗口列表更新失败: {_e}", exc_info=True)

        if self.after_id_window_update:
            self.app.root.after_cancel(self.after_id_window_update)

        self.after_id_window_update = self.app.root.after(1000, _update)

    def update_workdir(self, tid: Path | int) -> Path:
        """更新工作目录"""
        return self.workdir_manager.update_workdir(tid)


class ReminderManager:
    def __init__(self, todoer: TodoManager):
        self.todoer = todoer
        self.remainder_tid_old = set()
        self.remainders: dict[int, DaemonTimer] = {}
        DaemonTimer(2, self._init, )
        logger.debug("ReminderManager 初始化完成")

    def _init(self):
        for tid in json.loads(self.todoer.db_manager.get_setting("remainders", "[]")):
            record = self.todoer.db_manager.get_task(tid)
            if record:
                self.remainder_tid_old.add(tid)
                self.add(TaskItem(record, self.todoer))
        self._save()

    def _save(self):
        if self.remainder_tid_old != set(self.remainders.keys()):
            self.todoer.db_manager.set_setting("remainders", json.dumps(list(self.remainders.keys())))
            self.remainder_tid_old = set(self.remainders.keys())
            logger.info("Reminder list 已经更新...")
        # else:
        #     logger.debug(f"Reminder list 没有变化: {self.remainder_tid_old} != {set(self.remainders.keys())}")

    def delay(self, task: TodolistTaskModel, delay_min: int):
        self.todoer.db_manager.update_task(task.id, do_time=datetime.now() + timedelta(minutes=delay_min))
        task.do_time = task.do_time + timedelta(minutes=delay_min)
        self.add(task)

    def add(self, op: TaskItem | TodolistTaskModel):
        record = op.record if isinstance(op, TaskItem) else op
        if record.do_time <= datetime.now():
            threading.Thread(
                target=messagebox.showinfo, args=("提示", f"任务{record.title}已过期"), daemon=True
            ).start()
            return

        if record.id in self.remainders and self.remainders[record.id].is_alive():
            logger.debug(f"任务 {record.id}: {record.title} 的通知存在且等待中，已取消")
            self.remainders[record.id].cancel()

        self.remainders[record.id] = DaemonTimer(
            (record.do_time - datetime.now()).total_seconds(),
            toolkit_notify_callback,
            (record.title, record.desc),
            dict(
                duration="long",
                scenario='incomingCall',
                audio={'src': 'ms-winsoundevent:Notification.Looping.Alarm8', 'loop': 'true'},
                callbacks={
                    '延迟5min通知': lambda: self.delay(record, 5),
                    '延迟10min通知': lambda: self.delay(record, 10),
                    '清除通知': lambda: self.cancel(record),
                },
                timeout=60,
                timeout_callback=lambda: self.delay(record, 5),
            )
        )
        self.remainders[record.id].start()
        self._save()
        logger.info(
            f"任务 {record.id}: {record.title} 的定时器已经成功添加/更新到 「{record.do_time.strftime('%m-%d %H:%M')}」"
        )
        self.todoer.update_window()

    def is_notify(self, op: TaskItem | TodolistTaskModel | int):
        if isinstance(op, TaskItem):
            _id = op.record.id
        elif isinstance(op, TodolistTaskModel):
            _id = op.id
        else:
            _id = op
        return _id in self.remainders and self.remainders[_id].is_alive()

    def cancel(self, op: TaskItem | TodolistTaskModel):
        if isinstance(op, TaskItem):
            _id = op.record.id
            op = op.record
        elif isinstance(op, TodolistTaskModel):
            _id = op.id
        else:
            raise ValueError("Invalid task")

        if _id in self.remainders:
            if self.remainders[_id].is_alive():
                self.remainders[_id].cancel()
            del self.remainders[_id]
            self._save()
            logger.info(f"已经取消/完成任务 {_id}: {op.title} 的定时器")
            self.todoer.update_window()
        else:
            logger.debug(f"未找到任务 {_id}: {op.title} 的定时器")

    def change_time(self, op: TaskItem):
        if op.record.id not in self.remainders:
            return
        self.add(op)


class WorkdirManager:
    """名称规范
            0001-[status]-(worktime)-title

    """

    def __init__(self, todo: TodoManager):
        self.todo = todo
        self.todo_workdir = self.todo.app.config.todo_workdir
        self.re_name = re.compile(r"(\d{4})-(.*?)-\((.*?)\)-(.*)")
        DaemonTimer(120, self.flush_all).start()
        logger.debug("WorkdirManager 初始化完成")

    def to_name(self, task: TodolistTaskModel) -> str:
        return f"{task.id:04d}-{task.status_string()}-({task.work_time_occupied})-{self.title_to_filename(task.title)}".strip()

    def to_task(self, workdir: str):
        """将目录名转换为任务
        id, status, worktime, title
        """

        match = self.re_name.match(workdir)
        if not match:
            logger.error(f"目录 {workdir} 不符合命名规范")
            raise ValueError("目录名不符合命名规范")

        return TodolistTaskModel(
            id=int(match.group(1)),
            status=map_status_to_int.get(match.group(2)),
            work_time_occupied=int(match.group(3)),
            title=match.group(4),
        )

    def flush_all(self):
        """更新全部目录状态"""
        for workdir in self.todo_workdir.iterdir():
            workdir: Path
            # 如果只有README.md 移除目录
            items = [i.name for i in workdir.iterdir() if i.is_file() and i.name != "README.md"]
            if not items and not self.readme_has_data(workdir):
                workdir.joinpath("README.md").unlink(missing_ok=True)
                workdir.rmdir()
                logger.info(f"todolist workdir 移除空目录： {workdir.name}")
                continue

            self.update_workdir(workdir)

    def update_workdir(self, task: int | Path) -> Path:
        """更新指定目录状态"""

        if isinstance(task, Path):
            workdir = task
            old_info = self.to_task(task.name)
            new_info = self.todo.db_manager.get_task(old_info.id)
        else:
            new_info = self.todo.db_manager.get_task(task)
            workdir = list(self.todo_workdir.glob(f"{new_info.id:04d}-*"))
            workdir = workdir[0] if workdir else None

        if not (workdir and workdir.exists()):
            return self.create_workdir(new_info)

        old_info = self.to_task(workdir.name)
        # new_info = self.todoer.db_manager.get_task(old_info.id)
        if new_info and (
                new_info.status != old_info.status
                or new_info.work_time_occupied != old_info.work_time_occupied
                or self.title_to_filename(new_info.title) != old_info.title
        ):
            workdir = workdir.absolute()
            new_dir = workdir.rename(workdir.with_name(self.to_name(new_info)))
            self.create_readme(new_info, new_dir)
            logger.info(f"todolist workdir 目录名称更新： {workdir.name}")
            return new_dir
        return workdir

    def create_workdir(self, task: TodolistTaskModel) -> Path:
        """"""
        workdir = self.todo_workdir.joinpath(self.to_name(task))
        workdir.mkdir(parents=True, exist_ok=True)
        self.create_readme(task, workdir)
        logger.info(f"todolist workdir 创建目录： {workdir.name}")
        return workdir

    @staticmethod
    def readme_has_data(workdir: Path) -> bool:
        """判断目录下是否有数据"""
        readme = workdir.joinpath("README.md")
        if not readme.exists():
            return False
        if readme.stat().st_size == 0:
            return False
        if readme.read_text(encoding="utf-8").split("\n---\n# ")[-1].split("\n")[-1].strip() == "":
            logger.debug(f"文件 {workdir.name}/README.md 无自定义内容 ...")
            return False
        return True

    @staticmethod
    def create_readme(task: TodolistTaskModel, workdir: Path):
        """"""
        readme = workdir.joinpath("README.md")
        metadate = "---\n" + "\n".join(f"{k}: {v}" for k, v in task.to_dict().items()) + f"\n---\n# "
        old_date = readme.read_text(encoding="utf-8").split("\n---\n# ")[-1] if readme.exists() else f"{task.title}\n"
        readme.write_text(metadate + old_date, encoding="utf-8")
        logger.info(f"todolist workdir 创建 README.md： {workdir.name}")

    @staticmethod
    def title_to_filename(name: str) -> str:
        """将标题转换为文件名"""
        return re.sub(r"[\\/:*?\"<>|]", "_", name).strip()

# if __name__ == '__main__':
#     from ops_toolkit.config import config
#
#     logging.basicConfig(level=logging.INFO)
#
#
#     class App:
#         def __init__(self):
#             self.root = tk.Tk()
#             self.root.overrideredirect(True)  # 无边框
#             self.root.withdraw()  # 隐藏主窗口
#             self.config = config
#
#
#     _app = App()
#     tm = TodoManager(_app)
# tm.db_manager.add_record(title="测试任务 这是一个长任务", link="https://www.baidu.com")
# tm.show_display_window()
# work = WorkdirManager(tm)
# _tt = work.to_task("0001-[1]-(1)-test")
# print(_tt.__dict__)
# print(work.to_name(_tt))

# _app.root.mainloop()
