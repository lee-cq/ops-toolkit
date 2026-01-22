#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : monitor_teams_notification.py
@Author     : LeeCQ
@Date-Time  : 2026/1/19 01:01

依赖：
psutil opencv-python numpy
"""
import queue
import threading
import time
import psutil
import logging
import re

import cv2
import numpy as np
from PIL import ImageGrab, Image
from win11toast import toast

logger = logging.getLogger("ops_toolkit.monitor_teams_notification")


class Screenshot:
    def __init__(self, datetime: str, name: str, image: Image.Image, status: bool = False):
        self.datetime = datetime
        self.name = name
        self.image = image
        self.status = status


class NotificationMonitor:
    def __init__(self, app):
        self.app = app
        self.status_running = False
        self.status_notify = False
        self.counter_error = 0
        self.counter_checker = 0
        self.temp_screenshot = []
        self.queue_screenshots = queue.Queue(maxsize=2)

        # 默认的Teams图标坐标（需要根据实际情况校准）
        self.teams_icons = {
            'activity': self.icon_size_parse(self.app.config.teams.activity),  # 活动图标
            'teams':    self.icon_size_parse(self.app.config.teams.team),  # 团队图标
            'chat':     self.icon_size_parse(self.app.config.teams.chat),  # 聊天图标
            'tray':     self.icon_size_parse(self.app.config.teams.tray)  # 托盘图标
        }

    @staticmethod
    def icon_size_parse(icon_size: str) -> dict:
        """解析图标尺寸字符串"""
        match = re.compile(r"^(\d+)x(\d+)\+(\d+)\+(\d+)$").match(icon_size)
        if not match:
            logger.error(f"错误：图标尺寸格式错误 {icon_size}")
            return {}
        _s = {
            'x':      int(match.group(1)),
            'y':      int(match.group(2)),
            'width':  int(match.group(3)),
            'height': int(match.group(4)),
        }
        logger.debug(f"parse rest = {_s}")
        return _s

    @staticmethod
    def is_teams_running():
        """检查Teams是否正在运行"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'teams' in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    @staticmethod
    def is_screen_active() -> bool:
        """检查屏幕是否被锁定"""
        try:
            import ctypes.wintypes

            w_id = getattr(ctypes.windll.user32, "GetForegroundWindow")()
            if w_id == 0:
                return True

            w_length = getattr(ctypes.windll.user32, "GetWindowTextLengthW")(w_id) + 1
            w_title = ctypes.create_unicode_buffer(w_length)
            getattr(ctypes.windll.user32, "GetWindowTextW")(w_id, w_title, w_length)

            class_name = ctypes.create_unicode_buffer(256)
            getattr(ctypes.windll.user32, "GetClassNameW")(w_id, class_name, 256)

            logger.debug(f"前置窗口 class_name = {class_name.value}, w_title = {w_title.value}")
            if w_title.value == "Windows 默认锁屏界面" or class_name.value == "Windows.UI.Core.CoreWindow":
                return True

            return False

        except Exception as _e:
            print(f"检查屏幕是否被锁定时出错: {_e}")
            return False

    def check_teams_icon_have_red(self, icon_name) -> bool:
        """检查Teams图标是否有红色，默认认为有红色"""
        cords = self.teams_icons[icon_name]

        # 获取屏幕尺寸
        # screen_width = self.app.root.winfo_screenwidth()
        # screen_height = self.app.root.winfo_screenheight()

        # 确保坐标在屏幕范围内
        # x = max(0, min(cords['x'], screen_width))
        # y = max(0, min(cords['y'], screen_height))
        # width = min(cords['width'] + x , screen_width )
        # height = min(cords['height'] + y, screen_height)
        # logger.debug(f"优化后的坐标: {x}x{y}+{width}+{height}")

        # 确保区域不为空
        # if width <= 0 or height <= 0:
        #     logger.warning(f"错误：图标 {icon_name} 的坐标或尺寸无效: x={x}, y={y}, width={width}, height={height}")
        #     return True

        bbox = (cords['x'], cords['y'], cords['width'] + cords['x'], cords['height'] + cords['y'])
        # bbox = (x, y, width, height)
        screenshot = ImageGrab.grab(bbox=bbox)

        # 检查截图是否成功
        if screenshot is None:
            logger.warning(f"警告：截取图标 {icon_name} 区域失败，图像为None")
            return True

        _ss = Screenshot(
            datetime=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            name=icon_name,
            image=screenshot
        )

        self.temp_screenshot.append(_ss)

        image = np.array(screenshot)
        # 检查图像是否为空
        if image.size == 0:
            logger.warning(f"警告：截取图标 {icon_name} 区域失败，图像为空（可能屏幕被锁定或黑屏）")
            _ss.status = True
            return True

        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # 转换为HSV色彩空间
        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        except cv2.error as e:
            logger.warning(f"转换图像色彩空间时出错: {e}")
            _ss.status = True
            return True

        # 创建红色掩码（红色在HSV中有两个范围）
        mask1 = cv2.inRange(hsv, np.array([0, 128, 100]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(mask1, mask2)

        # 计算红色像素数量
        red_pixels = cv2.countNonZero(mask)
        _ss.status = red_pixels > 10
        return red_pixels > 10

    def notify(self, message: str):
        self.status_notify = True
        last_notify_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        logger.info(f"notify: {message}")
        while self.status_running:
            _ts = toast(
                app_id=self.app.config.app_name,
                title=f"Teams 告警",
                body=f"{last_notify_time}: {message}",
                duration="long",
                scenario='incomingCall',
                audio={'src': "ms-winsoundevent:Notification.Looping.Call3", 'loop': 'true'},
                tag="HourlyReminder"
            )
            if isinstance(_ts, dict) or "USER_CANCELED" in str(_ts):
                self.status_notify = False
                logger.info("用户消除了通知")
                break

    def check(self):
        self.counter_checker += 1
        logger.debug(f"check {self.counter_checker=}")
        if not self.is_teams_running():
            self.notify("Teams 未运行")
            return
        if self.is_screen_active():
            self.notify("屏幕已锁定")
            return

        _st = [self.check_teams_icon_have_red(ic) for ic in self.teams_icons]
        if self.queue_screenshots.full():
            self.queue_screenshots.get()
        self.queue_screenshots.put(self.temp_screenshot)
        logger.debug(f"向队列中添加了截图, {_st=}")
        self.temp_screenshot = []
        if any(_st):
            self.notify("Teams 图标有红色")

    def start(self):
        def run():
            logger.info("监控已经在线程中启动")
            while True:
                if not self.status_running:
                    self.stop()
                    logger.info(f"监控线程已经停止并退出, {self.status_running=}")
                    break
                try:
                    self.check()
                    self.counter_error = 0
                except Exception as _e:
                    logger.error(f"周期「{self.counter_checker}」检查状态时遇到问题: {_e}")
                    self.counter_error += 1
                    self.status_running = True
                    if self.counter_error >= 5:
                        self.notify("Teams 监控连续5次遇到问题")
                        self.stop()

                time.sleep(self.app.config.teams.interval)

        self.status_running = True
        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        logger.info("监控线程正在停止")
        self.status_running = False


if __name__ == '__main__':
    t = NotificationMonitor("")
    print(t.check_teams_icon_have_red("teams"))
