#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : clock.py
@Author     : LeeCQ
@Date-Time  : 2025/11/12 03:03
"""
import logging
import time
from datetime import datetime
from datetime import timedelta
from threading import Timer

from win11toast import notify

logger = logging.getLogger("translate.hourly_reminder")


class HourlyReminder(object):
    def __init__(self, app=None):
        self.app = app
        self.is_active = False
        self.timer: Timer | None = None
        self.next_hour: str = ""

    def _get_seconds_to_next_hour(self):
        # 计算当前时间到下一个整点的秒数
        now = datetime.now()
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        self.next_hour = next_hour.strftime("%H:%M")
        return (next_hour - now).total_seconds()

    def run(self):
        if not self.is_active:
            return
        try:
            notify(
                title=f"现在是{datetime.now().hour}点整",
                body="记得要巡检啊",
                duration="long",
                scenario='incomingCall',
                audio={'src': 'ms-winsoundevent:Notification.Looping.Alarm8', 'loop': 'true'}
            )
            logger.info("HourlyReminder notified.")
            time.sleep(5)

        finally:
            self.start()

    def start(self):
        """启动一个计时器"""
        self.is_active = True
        if self.timer is not None:
            self.timer.cancel()
        self.timer = Timer(self._get_seconds_to_next_hour(), self.run)
        self.timer.start()
        logger.info("HourlyReminder started.")

    def stop(self):
        self.is_active = False
        self.timer.cancel()
        self.timer = None
        self.next_hour = ""
        logger.info("HourlyReminder stopped.")
