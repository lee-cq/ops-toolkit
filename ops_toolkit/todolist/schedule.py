#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : schedule.py.py
@Author     : LeeCQ
@Date-Time  : 2026/3/17 07:17
"""
import json
import logging
import re
import typing
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

from pydantic import BaseModel
from pydantic import PrivateAttr

from ops_toolkit.tools import DaemonTimer

if typing.TYPE_CHECKING:
    from ops_toolkit.todolist.main import TodoManager

logger = logging.getLogger("ops_toolkit.todolist.scheduler")
DEFAULT_SCHEDULE_SETTING = json.dumps({
    "shifts_info": {
        "night": {
            "name":  "夜班",
            "start": "01:00",
            "end":   "09:00",
            "tasks": [
                "night_check",
                "morning_check",
            ]
        },
        "day":   {
            "name":  "日班",
            "start": "09:00",
            "end":   "18:00",
            "tasks": [
                "day_end",
            ]
        },
        "mid":   {
            "name":  "中班",
            "start": "17:00",
            "end":   "25:00",
            "tasks": [
                "retail_email",
                "production_issues"
            ]
        }
    },
    "tasks":       {
        "night_check":       {
            "name":    "夜班检查",
            "crons":   [
                "+0:00", "+6:30"
            ],
            "message": "请检查夜班任务是否完成"
        },
        "morning_check":     {
            "name":     "交易日晨检",
            "day_type": "工作日",
            "crons":    [
                "07:40"
            ],
            "message":  "准备开始晨检"
        },
        "day_end":           {
            "name":     "交易日DayEnd",
            "day_type": "工作日",
            "crons":    [
                "+0:00", "+6:30"
            ],
            "message":  "请检查日班任务是否完成"
        },
        "retail_email":      {
            "name":     "Retail邮件",
            "day_type": "ALL",
            "crons":    [
                "+07:00",
            ],
            "message":  "请检查Retail未回复邮件"
        },
        "production_issues": {
            "name":     "生产问题",
            "day_type": "ALL",
            "crons":    [
                "+06:00",
            ],
            "message":  "请检查并通知今日无进展的生产问题"
        }
    }
}, indent=2, ensure_ascii=False)


class Task(BaseModel):
    """班次任务"""
    name: str
    link: str = ""
    day_type: str | list = "ALL"
    crons: list[str]
    message: str = ""

    def get_day_type(self) -> list[str]:
        if self.day_type == "ALL":
            return ["工作日", "节假日", "带薪节假日"]
        elif isinstance(self.day_type, str):
            return [self.day_type]
        else:
            return self.day_type

    def get_crons(self, start_time: datetime) -> typing.Iterable[datetime]:
        """"""
        for cron in self.crons:
            if re.match(r"\+\d{1,2}:\d{1,2}", cron):
                _ = to_time_tuple(cron)
                yield start_time + timedelta(hours=_[0], minutes=_[1])
            elif re.match(r"^\d{1,2}:\d{1,2}", cron):
                _ = to_time_tuple(cron)
                yield start_time.replace(hour=_[0], minute=_[1])
            else:
                raise ValueError(f"时间格式错误： {cron}")

    def next_cron(self, start_time: datetime, now: datetime = datetime.now()) -> datetime | None:
        """"""
        for cron in self.get_crons(start_time):
            if cron > now:
                return cron
        return None


class Shift(BaseModel):
    """班次"""
    _all_tasks: dict[str, Task] = PrivateAttr(default_factory=dict)
    name: str
    start: str
    end: str
    tasks: list[Task | str]

    def get_tasks(self) -> typing.Iterable[Task]:
        for task in self.tasks:
            if isinstance(task, str):
                if task not in self._all_tasks:
                    raise ValueError(f"任务不存在,请检查配置： {task}")
                yield self._all_tasks[task]
            else:
                yield task

    @property
    def start_tuple(self) -> tuple[int, int]:
        return to_time_tuple(self.start)

    @property
    def end_tuple(self) -> tuple[int, int]:
        return to_time_tuple(self.end)

    @property
    def start_datetime(self, now: datetime = datetime.now()):
        if not self.on_shift(now):
            raise ValueError(f"{now.strftime('%Y-%m-%d %H:%M')} 不在班次时间段内")
        return datetime(now.year, now.month, now.day, *self.start_tuple)

    def on_shift(self, _t: datetime = datetime.now()) -> bool:
        _now = (_t.hour, _t.minute)
        if self.end_tuple[0] <= 24:
            if self.start_tuple <= _now < self.end_tuple:
                return True
            else:
                return False
        else:
            _new_end = (self.end_tuple[0] - 24, self.end_tuple[1])
            if self.start_tuple <= _now or _new_end > _now:
                return True
            return False


def to_time_tuple(t: str) -> tuple[int, int]:
    _ = t.strip().split(":")
    return int(_[0]), int(_[1])


class Shifts(BaseModel):
    night: Shift
    day: Shift
    mid: Shift

    def get_shift(self, sn: str) -> Shift:
        return getattr(self, sn)

    def get_offset(self) -> timedelta:
        """        """
        _ts = [[getattr(self, s).start_tuple, getattr(self, s).end_tuple] for s in self.model_fields_set]
        min_start = list(min([s[0] for s in _ts]))
        max_end = list(max([s[1] for s in _ts]))
        if max_end[0] >= 24:
            max_end[0] -= 24
        if min_start == max_end:
            logger.debug(f"确定班次时间偏移量： 「{min_start[0]}:{min_start[1]}」")
            return timedelta(hours=min_start[0], minutes=min_start[1])

        raise ValueError(f"班次时间段有重叠： {min_start=} {max_end=}")


class Scheduler(BaseModel):
    """班次任务管理器"""
    _todoer: "TodoManager" = PrivateAttr()
    shifts_info: Shifts
    tasks: dict[str, Task]

    @property
    def todoer(self) -> "TodoManager":
        return self._todoer

    def model_post_init(self, context: typing.Any, /) -> None:
        for field_name in self.shifts_info.model_fields_set:
            v = getattr(self.shifts_info, field_name)
            setattr(v, "_all_tasks", self.tasks)

    def save(self):
        self.todoer.db_manager.set_setting(
            "SchedulerShiftInfo",
            self.model_dump_json(indent=2, ensure_ascii=False)
        )

    @classmethod
    def load(cls, todoer: "TodoManager", new_config: str | None = None) -> "Scheduler":
        self = cls.model_validate_json(
            new_config if new_config else todoer.db_manager.get_setting("SchedulerShiftInfo", )
        )
        self._todoer = todoer
        return self


class ScheduleManager:
    """班次任务管理器"""

    def __init__(self, todoer: "TodoManager"):
        self.todoer = todoer
        self.scheduler: Scheduler = Scheduler.load(self.todoer, DEFAULT_SCHEDULE_SETTING)
        self.scheduler_start()

    def get_shift(self) -> Shift:
        """"""
        shift, _ = self.todoer.db_manager.get_day_shift(datetime.now() - self.scheduler.shifts_info.get_offset())
        if not shift:
            raise ValueError("未找到当前班次")
        shift = self.scheduler.shifts_info.get_shift(shift)
        if shift.on_shift():
            return shift
        raise ValueError("未找到当前班次")

    def scheduler_start(self):
        DaemonTimer(300, self.scheduler_start, ).start()
        try:
            self.scheduler_run()
        except Exception as e:
            logger.error(e)

    def scheduler_run(self):
        """运行任务"""
        shift = self.get_shift()
        day_shift, day_type = self.todoer.db_manager.get_day_shift(datetime.now())
        for task in shift.get_tasks():
            if task.day_type == "ALL" or day_type in task.day_type:
                self.check_remainder(task, shift)

    def check_remainder(self, task: Task, shift: Shift):
        next_cron: datetime = shift.next_cron(datetime.now(), task.next_cron(shift.start_datetime))
        if not next_cron:
            return

        r_name = f"[计划][{shift.name}] {task.name}"
        r_tasks = list(self.todoer.db_manager.query_task(r_name))
        if not r_tasks:
            r_task = self.todoer.db_manager.add_task(
                title=r_name,
                details=task.message,
                status=0,
                do_time=next_cron,
            )
            self.todoer.reminder_manager.add(r_task)
            return

        for r_task in r_tasks:
            self.todoer.db_manager.update_task(r_task.id, status=0, do_time=next_cron)
            self.todoer.reminder_manager.add(r_task)

    def scheduler_reload(self, new_config: str | None = None):
        self.scheduler = Scheduler.load(self.todoer, new_config)
        self.scheduler.save()
        return self.scheduler

    def add_shifts(self, ss: str):
        """"""
        rest: list[str] = []
        ss = ss.strip().split("\n")
        for ds in ss:
            try:
                match_result = re.match(
                    r'^(\d{4}[-/]\d{2}[-/]\d{2})[\t ]+(day|mid|night)[\t ]+(工作日|节假日|带薪节假日)$',
                    ds
                )
                if not match_result:
                    rest.append(ds + " E: 班次信息格式匹配失败")
                ds = match_result.groups()
                self.todoer.db_manager.set_day_shift(ds[0].replace("/", "-"), ds[1], ds[2])
            except Exception as e:
                rest.append(str(ds) + " E: " + str(e))
            else:
                logger.info(f"全部每日班次信息添加或更新成功。")
        if rest:
            logger.error("添加失败：\n" + "\n".join(rest))
            messagebox.showwarning("提示",
                                   "格式：^(\\d{4}[-/]\\d{2}[-/]\\d{2})[\\t ]+(day|mid|night)[\\t ]+(工作日|节假日|带薪节假日)$ \n"
                                   "例如：2026-03-03 day 工作日\n下面的内容添加失败：\n" + "\n".join(rest))

    def show_edit_shift_info_window(self):
        _w = tk.Toplevel(self.todoer.app.root)
        _w.title("编辑班次任务信息")
        _w.geometry("500x650")

        # 创建ScrolledText
        text_area = ScrolledText(_w, wrap=tk.WORD, font=("Arial", 12))
        text_area.pack(pady=10, expand=True)

        # 创建按钮框架
        button_frame = tk.Frame(_w)
        button_frame.pack(pady=10)

        # 创建“从配置中重载”按钮
        reload_button = tk.Button(
            button_frame,
            text="从配置中重载",
            command=lambda: (
                text_area.delete("1.0", tk.END),
                text_area.insert("1.0", self.scheduler.model_dump_json(exclude={"todoer"}))
            )
        )
        reload_button.pack(side='left', padx=5)

        # 创建“保存”按钮
        save_button = tk.Button(
            button_frame,
            text="保存",
            command=lambda: self.scheduler_reload(text_area.get("1.0", tk.END)))
        save_button.pack(side='left', padx=5)

        # 创建“帮助”按钮
        help_button = tk.Button(button_frame, text="帮助",
                                command=lambda: messagebox.showinfo("帮助", "班次信息格式为：JSON\n"))
        help_button.pack(side='left', padx=5)

    def show_add_work_window(self):
        _w = tk.Toplevel(self.todoer.app.root)
        _w.title("编辑班次任务信息")
        _w.geometry("500x650")

        # 创建ScrolledText
        text_area = ScrolledText(_w, wrap=tk.WORD, font=("Arial", 12))
        text_area.pack(pady=10, expand=True)

        # 创建按钮框架
        button_frame = tk.Frame(_w)
        button_frame.pack(pady=10)

        # 创建“保存”按钮
        save_button = tk.Button(
            button_frame,
            text="添加",
            command=lambda: self.add_shifts(text_area.get("1.0", tk.END)))
        save_button.pack(side='left', padx=5)

        # 创建“帮助”按钮
        help_button = tk.Button(
            button_frame,
            text="帮助",
            command=lambda: messagebox.showinfo("帮助",
                                                "班次信息格式为：[YYYY-mm-dd] [day|night|mid] [节假日|工作日|带薪节假日]\n"))
        help_button.pack(side='left', padx=5)
