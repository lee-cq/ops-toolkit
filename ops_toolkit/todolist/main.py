import json
import tkinter as tk
import typing
import logging
from datetime import datetime
from threading import Timer
from tkinter import messagebox

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

    def show_create_window(self):
        """显示创建窗口"""
        TodoCreateWindow(self)

    def show_display_window(self):
        """显示展示窗口"""
        self.floating_window.show()

    def update_window(self):
        """更新窗口"""
        self.floating_window.load_tasks()


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
    tm.show_display_window()

    _app.root.mainloop()
