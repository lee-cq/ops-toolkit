import tkinter as tk
import typing
import logging

from ops_toolkit.todolist.models import TodolistManager
from ops_toolkit.todolist.ui_create_window import TodoCreateWindow
from ops_toolkit.todolist.ui_floating_window import FloatingWindow

if typing.TYPE_CHECKING:
    from ops_toolkit.app import App

logger = logging.getLogger("ops-toolkit.todolist.main")


class TodoManager:
    """待办事项管理器"""

    def __init__(self, app: "App"):
        self.app = app
        self.db_manager = TodolistManager(self.app)

        self.floating_window = FloatingWindow(self.app, self.db_manager)

    def show_create_window(self):
        """显示创建窗口"""
        TodoCreateWindow(self)

    def show_display_window(self):
        """显示展示窗口"""
        self.floating_window.show()

    def update_window(self):
        """更新窗口"""
        self.floating_window.load_tasks()


if __name__ == '__main__':
    from ops_toolkit.config import config


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
