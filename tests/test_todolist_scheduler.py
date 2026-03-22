#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : test_todolist_scheduler.py
@Author     : LeeCQ
@Date-Time  : 2026/3/19 17:08
"""
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from ops_toolkit.todolist.schedule import DEFAULT_SCHEDULE_SETTING
from ops_toolkit.todolist.schedule import Task, Shift, Shifts, Scheduler, ScheduleManager
from ops_toolkit.todolist.main import TodoManager
from ops_toolkit.todolist.schedule import to_time_tuple


class TestTask(unittest.TestCase):
    """测试 Task 类"""

    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            name="测试任务",
            crons=["0 9 * * *", "0 18 * * *"],
            message="这是一个测试任务"
        )
        self.assertEqual(task.name, "测试任务")
        self.assertEqual(task.crons, ["0 9 * * *", "0 18 * * *"])
        self.assertEqual(task.message, "这是一个测试任务")

    def test_task_with_single_cron(self):
        """测试单个 cron 表达式的任务"""
        task = Task(
            name="单次任务",
            crons=["0 12 * * *"],
            message="每天中午执行"
        )
        self.assertEqual(len(task.crons), 1)
        self.assertEqual(task.crons[0], "0 12 * * *")


class TestShift(unittest.TestCase):
    """测试 Shift 类"""

    def test_shift_creation(self):
        """测试班次创建"""
        shift = Shift(
            name="早班",
            start="09:00",
            end="17:00",
            tasks=["task1", "task2"]
        )
        self.assertEqual(shift.name, "早班")
        self.assertEqual(shift.start, "09:00")
        self.assertEqual(shift.end, "17:00")
        self.assertEqual(shift.start_tuple, (9, 0))
        self.assertEqual(shift.end_tuple, (17, 0))
        self.assertEqual(shift.on_shift(datetime(2024, 3, 17, 10, 30)), True)
        self.assertEqual(shift.on_shift(datetime(2024, 3, 17, 9, 0)), True)
        self.assertEqual(shift.on_shift(datetime(2024, 3, 17, 17, 1)), False)
        self.assertEqual(len(shift.tasks), 2)

    def test_to_time_tuple(self):
        """测试时间字符串转换为元组"""
        result = to_time_tuple("09:30")
        self.assertEqual(result, (9, 30))

        result = to_time_tuple("23:59")
        self.assertEqual(result, (23, 59))

        result = to_time_tuple(" 08:00 ")
        self.assertEqual(result, (8, 0))

    def test_start_tuple_property(self):
        """测试开始时间属性"""
        shift = Shift(name="测试", start="07:15", end="15:30", tasks=[])
        self.assertEqual(shift.start_tuple, (7, 15))

    def test_end_tuple_property(self):
        """测试结束时间属性"""
        shift = Shift(name="测试", start="07:15", end="15:30", tasks=[])
        self.assertEqual(shift.end_tuple, (15, 30))

    def test_on_shift_normal_hours(self):
        """测试正常工作时间内的班次判断"""
        # 白班：08:00 - 16:00
        shift = Shift(name="白班", start="08:00", end="16:00", tasks=[])

        # 在班次时间内
        test_time = datetime(2024, 3, 17, 10, 30)
        self.assertTrue(shift.on_shift(test_time))

        # 在班次开始前
        test_time = datetime(2024, 3, 17, 7, 30)
        self.assertFalse(shift.on_shift(test_time))

        # 在班次结束后
        test_time = datetime(2024, 3, 17, 17, 0)
        self.assertFalse(shift.on_shift(test_time))

        # 刚好在开始时间
        test_time = datetime(2024, 3, 17, 8, 0)
        self.assertTrue(shift.on_shift(test_time))

        # 刚好在结束时间
        test_time = datetime(2024, 3, 17, 16, 0)
        self.assertTrue(shift.on_shift(test_time))

    def test_on_shift_overnight_hours(self):
        """测试跨夜班次的判断"""
        # 夜班：22:00 - 次日 06:00
        shift = Shift(name="夜班", start="22:00", end="30:00", tasks=[])

        # 在夜班时间内（晚上）
        test_time = datetime(2024, 3, 17, 23, 0)
        self.assertTrue(shift.on_shift(test_time))

        # 在夜班时间内（凌晨）
        test_time = datetime(2024, 3, 18, 2, 0)
        self.assertTrue(shift.on_shift(test_time))

        # 不在夜班时间内（上午）
        test_time = datetime(2024, 3, 17, 10, 0)
        self.assertFalse(shift.on_shift(test_time))

        # 刚好在开始时间
        test_time = datetime(2024, 3, 17, 22, 0)
        self.assertTrue(shift.on_shift(test_time))

        # 刚好在结束时间
        test_time = datetime(2024, 3, 18, 6, 0)
        self.assertFalse(shift.on_shift(test_time))

    def test_on_shift_default_time(self):
        """测试使用默认当前时间的班次判断"""
        shift = Shift(name="白班", start="08:00", end="16:00", tasks=[])
        # 不传入时间，使用默认值
        result = shift.on_shift()
        # 只验证返回的是布尔值
        self.assertIsInstance(result, bool)


class TestShifts(unittest.TestCase):
    """测试 Shifts 类"""

    def test_shifts_creation(self):
        """测试 Shifts 创建"""
        shifts = Shifts(
            night=Shift(name="夜班", start="22:00", end="30:00", tasks=[]),
            day=Shift(name="白班", start="08:00", end="16:00", tasks=[]),
            mid=Shift(name="中班", start="16:00", end="24:00", tasks=[])
        )
        self.assertIsNotNone(shifts.night)
        self.assertIsNotNone(shifts.day)
        self.assertIsNotNone(shifts.mid)
        self.assertEqual(shifts.day.name, "白班")

    def test_get_shift(self):
        """测试获取指定班次"""
        shifts = Shifts(
            night=Shift(name="夜班", start="22:00", end="30:00", tasks=[]),
            day=Shift(name="白班", start="08:00", end="16:00", tasks=[]),
            mid=Shift(name="中班", start="16:00", end="24:00", tasks=[])
        )
        shift = shifts.get_shift("day")
        self.assertEqual(shift.name, "白班")

        shift = shifts.get_shift("night")
        self.assertEqual(shift.name, "夜班")

        shift = shifts.get_shift("mid")
        self.assertEqual(shift.name, "中班")

    def test_get_offset_success(self):
        """测试成功获取偏移量"""
        shifts = Shifts(
            night=Shift(name="夜班", start="23:00", end="32:00", tasks=[]),
            day=Shift(name="白班", start="08:00", end="16:00", tasks=[]),
            mid=Shift(name="中班", start="16:00", end="24:00", tasks=[])
        )
        offset = shifts.get_offset()
        self.assertIsInstance(offset, timedelta)
        # 最早开始时间是 08:00
        mm, ss = divmod(offset.seconds, 60)
        hh, mm = divmod(mm, 60)
        self.assertEqual(hh, 8)
        self.assertEqual(mm, 0)  # 分钟数

    def test_get_offset_with_midnight_end(self):
        """测试结束时间为 24 点的情况"""
        shifts = Shifts(
            night=Shift(name="夜班", start="22:00", end="32:00", tasks=[]),
            day=Shift(name="白班", start="08:00", end="16:00", tasks=[]),
            mid=Shift(name="中班", start="16:00", end="24:00", tasks=[])
        )
        offset = shifts.get_offset()
        self.assertIsInstance(offset, timedelta)

    def test_get_offset_error_on_overlap(self):
        """测试时间段重叠时抛出异常"""
        # 创建时间段重叠的班次
        with self.assertRaises(ValueError):
            Shifts(
                night=Shift(name="夜班", start="08:00", end="10:00", tasks=[]),
                day=Shift(name="白班", start="08:00", end="16:00", tasks=[]),
                mid=Shift(name="中班", start="16:00", end="24:00", tasks=[])
            ).get_offset()


class TestScheduler(unittest.TestCase):
    """测试 Scheduler 类"""

    def setUp(self):
        """准备测试数据"""
        from ops_toolkit.todolist.models import DBManager
        from ops_toolkit.todolist.main import ReminderManager

        self.todoer_mock = Mock(spec=TodoManager)
        self.todoer_mock.db_manager = DBManager()
        self.todoer_mock.reminder_manager = Mock(spec=ReminderManager)

        self.scheduler = Scheduler.load(
            todoer=self.todoer_mock,
            new_config=DEFAULT_SCHEDULE_SETTING
        )

    def test_scheduler_creation(self):
        """测试 Scheduler 创建"""
        self.assertIsNotNone(self.scheduler.todoer)
        self.assertIsNotNone(self.scheduler.shifts_info)
        self.assertGreater(len(self.scheduler.tasks), 0)

    def test_save(self):
        """测试保存配置"""
        self.assertTrue(self.scheduler.save())

    def test_load_from_db(self):
        """测试从数据库加载 Scheduler"""
        self.todoer_mock.db_manager.set_setting("SchedulerShiftInfo", DEFAULT_SCHEDULE_SETTING)
        result = Scheduler.load(self.todoer_mock)
        # self.assertIsInstance(result, Scheduler)
        self.assertIsInstance(result.shifts_info, Shifts)
        self.assertIsInstance(result.tasks, dict)
        self.assertIsInstance(result.tasks.popitem()[1], Task)


class TestScheduleManager(unittest.TestCase):
    """测试 ScheduleManager 类"""

    def setUp(self):
        """准备测试数据"""
        from ops_toolkit.todolist.models import DBManager
        from ops_toolkit.todolist.main import ReminderManager

        self.todoer_mock = Mock(spec=TodoManager)
        self.todoer_mock.db_manager = DBManager()
        self.todoer_mock.reminder_manager = ReminderManager(self.todoer_mock)
        self.todoer_mock.db_manager.set_day_shift("2024-03-17", "day", "工作日")  # 设置默认班次
        self.now = datetime(2024, 3, 17, 10, 0)

        self.manager = ScheduleManager(self.todoer_mock)

    @patch('ops_toolkit.todolist.schedule.datetime')
    def test_get_shift_success(self, mock_datetime):
        """测试成功获取当前班次"""
        mock_now = self.now
        mock_datetime.now.return_value = mock_now

        with patch.object(self.manager.scheduler.shifts_info, 'get_offset', return_value=timedelta(hours=8)):
            with patch.object(self.manager.scheduler, 'get_shift', return_value=self.shifts_info.day):
                with patch.object(self.shifts_info.day, 'on_shift', return_value=True):
                    result = self.manager.get_shift()
                    self.assertEqual(result, self.shifts_info.day)

    @patch('ops_toolkit.todolist.schedule.datetime')
    def test_get_shift_not_found(self, mock_datetime):
        """测试未找到当前班次时抛出异常"""
        mock_now = datetime(2024, 3, 17, 10, 0)
        mock_datetime.now.return_value = mock_now

        with patch.object(self.manager.scheduler.shifts_info, 'get_offset', return_value=timedelta(hours=8)):
            with patch.object(self.manager.scheduler, 'get_shift', return_value=self.shifts_info.day):
                with patch.object(self.shifts_info.day, 'on_shift', return_value=False):
                    with self.assertRaises(ValueError) as context:
                        self.manager.get_shift()
                    self.assertEqual(str(context.exception), "未找到当前班次")

    @patch.object(ScheduleManager, 'scheduler_reload')
    def test_scheduler_reload(self, mock_reload):
        """测试重新加载调度器配置"""
        new_config = '{"new": "config"}'
        self.manager.scheduler_reload(new_config)
        mock_reload.assert_called_once_with(new_config)

    @patch('ops_toolkit.todolist.schedule.messagebox')
    def test_add_shifts_success(self, mock_messagebox):
        """测试添加班次信息成功"""
        shifts_data = "2024-03-17 day 工作日\n2024-03-18 night 节假日"

        with patch.object(self.todoer_mock.db_manager, 'set_shift') as mock_set_shift:
            self.manager.add_shifts(shifts_data)
            self.assertEqual(mock_set_shift.call_count, 2)
            mock_messagebox.showwarning.assert_not_called()

    @patch('ops_toolkit.todolist.schedule.messagebox')
    def test_add_shifts_with_errors(self, mock_messagebox):
        """测试添加班次信息有错误"""
        shifts_data = "invalid data\n2024-03-17 day 工作日"

        with patch.object(self.todoer_mock.db_manager, 'set_shift', side_effect=[ValueError("格式错误"), None]):
            self.manager.add_shifts(shifts_data)
            mock_messagebox.showwarning.assert_called_once()
            call_args = mock_messagebox.showwarning.call_args
            self.assertIn("E: 格式错误", call_args[0][1])

    @patch('ops_toolkit.todolist.schedule.tk.Toplevel')
    def test_show_edit_shift_info_window(self, mock_toplevel):
        """测试显示编辑班次信息窗口"""
        mock_window = Mock()
        mock_toplevel.return_value = mock_window

        with patch('ops_toolkit.todolist.schedule.ScrolledText') as mock_text:
            with patch('ops_toolkit.todolist.schedule.tk.Frame') as mock_frame:
                self.manager.show_edit_shift_info_window()
                mock_toplevel.assert_called_once()
                mock_text.assert_called_once()

    @patch('ops_toolkit.todolist.schedule.tk.Toplevel')
    def test_show_add_work_window(self, mock_toplevel):
        """测试显示添加工作窗口"""
        mock_window = Mock()
        mock_toplevel.return_value = mock_window

        with patch('ops_toolkit.todolist.schedule.ScrolledText') as mock_text:
            with patch('ops_toolkit.todolist.schedule.tk.Frame') as mock_frame:
                self.manager.show_add_work_window()
                mock_toplevel.assert_called_once()
                mock_text.assert_called_once()


if __name__ == '__main__':
    unittest.main()
