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

import cv2
import numpy as np
from PIL import ImageGrab, Image
from win11toast import toast

logger = logging.getLogger("translate.monitor_teams_notification")


class Screenshot:
    def __init__(self, datetime: str, name: str, image: Image.Image):
        self.datetime = datetime
        self.name = name
        self.image = image


class NotificationMonitor:
    def __init__(self, app):
        self.app = app
        self.status_running = False
        self.counter_error = 0
        self.temp_screenshot = []
        self.queue_screenshots = queue.Queue(maxsize=5)

        # 默认的Teams图标坐标（需要根据实际情况校准）
        self.teams_icons = {
            'activity': {'x': 100, 'y': 50, 'width': 30, 'height': 30},  # 活动图标
            'teams':    {'x': 150, 'y': 50, 'width': 30, 'height': 30},  # 团队图标
            'chat':     {'x': 200, 'y': 50, 'width': 30, 'height': 30},  # 聊天图标
            'tray':     {'x': 1422, 'y': 1039, 'width': 30, 'height': 30}  # 托盘图标
        }

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

    def check_teams_icon_have_red(self, icon_name) -> bool:
        """检查Teams图标是否有红色，默认认为有红色"""
        cords = self.teams_icons[icon_name]

        # 获取屏幕尺寸
        screen_width = self.app.root.winfo_screenwidth()
        screen_height = self.app.root.winfo_screenheight()

        # 确保坐标在屏幕范围内
        x = max(0, min(cords['x'], screen_width))
        y = max(0, min(cords['y'], screen_height))
        width = min(cords['width'], screen_width - x)
        height = min(cords['height'], screen_height - y)

        # 确保区域不为空
        if width <= 0 or height <= 0:
            logger.warning(f"错误：图标 {icon_name} 的坐标或尺寸无效: x={x}, y={y}, width={width}, height={height}")
            return True
        bbox = (x, y, x + width, y + height)
        screenshot = ImageGrab.grab(bbox=bbox)

        # 检查截图是否成功
        if screenshot is None:
            logger.warning(f"警告：截取图标 {icon_name} 区域失败，图像为None")
            return True

        self.temp_screenshot.append(Screenshot(
            datetime=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            name=icon_name,
            image=screenshot
        ))

        image = np.array(screenshot)
        # 检查图像是否为空
        if image.size == 0:
            logger.warning(f"警告：截取图标 {icon_name} 区域失败，图像为空（可能屏幕被锁定或黑屏）")
            return True

        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # 转换为HSV色彩空间
        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        except cv2.error as e:
            logger.warning(f"转换图像色彩空间时出错: {e}")
            return True

        # 创建红色掩码（红色在HSV中有两个范围）
        mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(mask1, mask2)

        # 计算红色像素数量
        red_pixels = cv2.countNonZero(mask)

        # 如果红色像素超过阈值，则认为检测到通知
        return red_pixels > 10

    def notify(self, message: str):
        last_notify_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        while self.status_running:

            _ts = toast(
                title=f"Teams 告警",
                body=f"{last_notify_time}: {message}",
                duration="long",
                scenario='incomingCall',
                audio={'src': "ms-winsoundevent:Notification.Looping.Call3", 'loop': 'true'},
                tag="HourlyReminder"
            )
            if isinstance(_ts, dict) or "USER_CANCELED" in str(_ts):
                break

    def check(self):
        if not self.is_teams_running():
            self.notify("Teams 未运行")

        if any(self.check_teams_icon_have_red(ic) for ic in self.teams_icons):
            self.notify("Teams 图标有红色")
        if self.queue_screenshots.full():
            self.queue_screenshots.get()
        self.queue_screenshots.put(self.temp_screenshot)
        self.temp_screenshot = []

    def start(self):
        def run():
            while True:
                if not self.status_running:
                    logger.info("监控已经停止")
                    self.stop()
                    break
                self.check()
                time.sleep(5)

        self.status_running = True
        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self.status_running = False


if __name__ == '__main__':
    t = NotificationMonitor("")
    print(t.check_teams_icon_have_red("teams"))
