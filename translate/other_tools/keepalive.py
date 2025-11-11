#!/usr/bin/env python3
# coding: utf-8
"""
@File Name  : keepalive.py
@Author     : LeeCQ
@Date-Time  : 2025/11/12 02:42

保持电脑处于活跃状态
监听键盘和鼠标的活跃情况，如果30s无操作，按下Ctrl键
"""
import logging
import threading
import time
from pynput import keyboard, mouse
from pynput.keyboard import Controller

logger = logging.getLogger("translate.keepalive")


def beautiful_second(second) -> str:
    """将秒数格式化为易读的字符串"""
    h, m = divmod(second, 3600)
    m, s = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"


class Keepalive:

    def __init__(self, timeout=120, period=30):
        self.last_activity_time = time.time()
        self.timeout = timeout
        self.period = period
        self._running = False

        self.ctrl_press_count = 0
        self.keepalive_time = 0
        self.living_time = 0

        # 初始化键盘控制器，用于模拟按键
        self.keyboard_controller = Controller()

    def on_activity(self, *args):
        """更新最后一次活动时间"""
        self.last_activity_time = time.time()

    def check_idle(self):
        """检查是否超时，如果超时则按下Ctrl键"""
        if time.time() - self.last_activity_time > self.timeout:
            self.keepalive_time += self.timeout
            self.ctrl_press_count += 1
            logger.info(f"按下 {self.ctrl_press_count} 次Ctrl键，已保持活跃 {beautiful_second(self.keepalive_time)}")
            # 按下并释放Ctrl键
            with self.keyboard_controller.pressed(keyboard.Key.ctrl):
                pass
            # 重置活动时间，避免连续触发
            self.on_activity()
        else:
            self.living_time += self.period

    def main(self):
        logger.info("Keepalive @ LeeCQ, Version 2.2")
        logger.info(f"开始监控键盘鼠标活动，{self.timeout}秒无操作将自动按下Ctrl键...")
        self._running = True

        # 设置鼠标监听器
        mouse_listener = mouse.Listener(
            on_move=lambda x, y: self.on_activity(),
            on_click=lambda x, y, button, pressed: self.on_activity(),
            on_scroll=lambda x, y, dx, dy: self.on_activity()
        )

        # 设置键盘键盘监听器
        keyboard_listener = keyboard.Listener(
            on_press=lambda key: self.on_activity(),
            on_release=lambda key: self.on_activity()
        )

        # 启动监听器
        mouse_listener.start()
        keyboard_listener.start()

        try:
            # 主循环，定期检查是否超时
            while True:
                if self.check_exit():
                    logger.info("Keepalive exited.")
                    break
                self.check_idle()
                time.sleep(self.period)  # 每秒检查一次
        except KeyboardInterrupt:
            logger.info("\n程序已退出")
        finally:
            # 停止监听器
            mouse_listener.stop()
            keyboard_listener.stop()

    def stop(self):
        logger.info("Keepalive will be stopped at next period.")
        self._running = False

    def start(self):
        threading.Thread(target=self.main, daemon=True, name="keepalive").start()

    def is_running(self):
        return self._running

    def check_exit(self):
        if self._running:
            return False

        return True


def main():
    # TODO 添加命令行参数 timeout, period
    Keepalive().main()


if __name__ == "__main__":
    Keepalive().main()
