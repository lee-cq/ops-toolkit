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

    def _get_seconds_to_next_hour(self, after=1):
        # 计算当前时间到下一个整点的秒数
        now = datetime.now()
        next_hour = (now + timedelta(hours=after)).replace(minute=0, second=0, microsecond=0)
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

    def start(self, after=1):
        """启动一个计时器"""
        self.is_active = True
        if self.timer is not None:
            self.timer.cancel()
        self.timer = Timer(self._get_seconds_to_next_hour(after), self.run)
        self.timer.start()
        logger.info(f"HourlyReminder started. {after=} {self.next_hour=}")

    def stop(self):
        """停止计时器"""
        self.is_active = False
        self.next_hour = ""
        if self.timer:
            self.timer.cancel()
            self.timer = None
            logger.info("HourlyReminder stopped.")
