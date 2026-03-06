import json
import re
import tkinter as tk
import typing
import logging
from datetime import datetime
from pathlib import Path
from threading import Timer
from tkinter import messagebox

from ops_toolkit.todolist.models import TodolistTaskModel
from ops_toolkit.todolist.models import DBManager
from ops_toolkit.todolist.ui_create_window import TodoCreateWindow
from ops_toolkit.todolist.ui_floating_window import FloatingWindow
from ops_toolkit.todolist.ui_floating_window import TaskItem
from ops_toolkit.tools import toolkit_notify

if typing.TYPE_CHECKING:
    from ops_toolkit.app import App

logger = logging.getLogger("ops_toolkit.todolist.main")


class TodoManager:
    """待办事项管理器"""

    def __init__(self, app: "App"):
        self.app = app
        self.db_manager = DBManager(self.app)

        self.floating_window: FloatingWindow = FloatingWindow(self.app, self)
        self.reminder_manager: ReminderManager = ReminderManager(self)
        self.workdir_manager: WorkdirManager = WorkdirManager(self)

    def show_create_window(self):
        """显示创建窗口"""
        TodoCreateWindow(self)

    def show_display_window(self):
        """显示展示窗口"""
        self.floating_window.show()

    def update_window(self):
        """更新窗口"""
        self.floating_window.load_tasks()

    def update_workdir(self, tid: Path | int) -> Path:
        """更新工作目录"""
        return self.workdir_manager.update_workdir(tid)


class ReminderManager:
    def __init__(self, todo_manager: TodoManager):
        self.todo_manager = todo_manager
        self.remainder_tid_old = set()
        self.remainders: dict[int, Timer] = {}
        self._init()

    def _init(self):
        for tid in json.loads(self.todo_manager.db_manager.get_setting("remainders", "[]")):
            record = self.todo_manager.db_manager.get_task(tid)
            if record:
                self.remainder_tid_old.add(tid)
                self.add(TaskItem(record, self.todo_manager))
        self._save()

    def _save(self):
        if self.remainder_tid_old != self.remainders.keys():
            self.todo_manager.db_manager.set_setting("remainders", json.dumps(list(self.remainders.keys())))
            self.remainder_tid_old = self.remainders.keys()
            logger.info("Reminder list 已经更新...")

    def add(self, op: TaskItem):
        if op.record.do_time <= datetime.now():
            messagebox.showinfo("提示", f"任务{op.record.title}已过期")
            return

        if op.record.id in self.remainders and self.remainders[op.record.id].is_alive():
            self.remainders[op.record.id].cancel()
            logger.info(f"任务 {op.record.title} 的定时器已经存在, 旧任务已取消")

        self.remainders[op.record.id] = Timer(
            (op.record.do_time - datetime.now()).total_seconds(),
            toolkit_notify,
            (op.record.title, op.record.desc),
            # {"launch": True}
        )
        self.remainders[op.record.id].start()
        self._save()
        logger.info(f"任务 {op.record.id}: {op.record.title} 的定时器已经成功添加并启动")

    def is_notify(self, op: TaskItem | int):
        _id = op.record.id if isinstance(op, TaskItem) else op
        return _id in self.remainders and self.remainders[_id].is_alive()

    def cancel(self, op: TaskItem | int):
        _id = op.record.id if isinstance(op, TaskItem) else op
        if _id in self.remainders:
            if self.remainders[_id].is_alive():
                self.remainders[_id].cancel()
            del self.remainders[_id]
            self._save()
            logger.info(f"已经取消/完成任务 {_id}: {op.record.title} 的定时器")
        else:
            logger.debug(f"未找到任务 {_id}: {op.record.title} 的定时器")

    def change_time(self, op: TaskItem):
        if op.record.id not in self.remainders:
            return
        self.add(op)


class WorkdirManager:
    """名称规范
            0001-[status]-(worktime)-title

    """
    map_status_to_int = {
        "未开始": 0,
        "进行中": 1,
        "已完成": 2,
        "已取消": 3,
    }
    map_int_to_status = {v: k for k, v in map_status_to_int.items()}

    def __init__(self, todo: TodoManager):
        self.todo = todo
        self.todo_workdir = self.todo.app.config.todo_workdir
        self.re_name = re.compile(r"(\d{4})-\[(.*?)]-\((.*?)\)-(.*)")
        Timer(120, self.flush_all).start()

    def to_name(self, task: TodolistTaskModel) -> str:
        return f"{task.id:04d}-[{self.map_int_to_status.get(task.status)}]-({task.work_time_occupied})-{self.title_to_filename(task.title)}"

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
            status=self.map_status_to_int.get(match.group(2)),
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
        # new_info = self.todo.db_manager.get_task(old_info.id)
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

    def readme_has_data(self, workdir: Path) -> bool:
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
        """
        将标题转换为文件名
        """
        return re.sub(r"[\\/:*?\"<>|]", "_", name)


if __name__ == '__main__':
    from ops_toolkit.config import config

    logging.basicConfig(level=logging.INFO)


    class App:
        def __init__(self):
            self.root = tk.Tk()
            self.root.overrideredirect(True)  # 无边框
            self.root.withdraw()  # 隐藏主窗口
            self.config = config


    _app = App()
    tm = TodoManager(_app)
    # tm.db_manager.add_record(title="测试任务 这是一个长任务", link="https://www.baidu.com")
    # tm.show_display_window()
    work = WorkdirManager(tm)
    _tt = work.to_task("0001-[1]-(1)-test")
    print(_tt.__dict__)
    print(work.to_name(_tt))

    # _app.root.mainloop()
