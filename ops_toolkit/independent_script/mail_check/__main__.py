#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : __main__
@Author     : LeeCQ
@Date-Time  : 2026/8/17 

mail-check:
    morning-check:
        args: 0800, 0818, 0836, 0901, 0915: 时间
        -r， --report, 发送报告

    no-replay:
        -r, --report 发送报告

"""

import argparse
import logging
import logging.config
import sys
from datetime import date

from pathlib import Path

from utils import SCRIPT_DIR

logger = logging.getLogger(__name__)
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "deps"))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s",
)
log_path = SCRIPT_DIR / "logs"
log_path.mkdir(parents=True, exist_ok=True)


def _init_log(log_name):
    log_config = {
        'version': 1,
        # 'disable_existing_loggers': False,
        'formatters': {
            'translate_formatter': {
                'format': '%(asctime)s - %(filename)s[%(lineno)d] - [%(levelname)s] - %(message)s',
                # 包含时间、logname、等级、msg
                'datefmt': '%Y-%m-%d %H:%M:%S'  # 时间格式
            },
        },
        'handlers': {
            'console_handler': {
                'class': 'logging.StreamHandler',  # 控制台输出
                'formatter': 'translate_formatter',
                'level': 'DEBUG'  # 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
            },
            'file_handler': {
                'class': 'logging.FileHandler',  # 文件输出
                'filename': log_name,  # 日志文件名
                'formatter': 'translate_formatter',
                'level': 'DEBUG',  # 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
                "encoding": "utf-8"
            },
        },
        "filters": {},
        "root": {
            'handlers': ['console_handler', 'file_handler'],
            'level': 'DEBUG',
            'propagate': True  # 不向上传播日志
        },
    }
    logging.config.dictConfig(log_config)


def handle_morning_check(args):
    """处理 morning-check 子命令"""
    time_list = args.times
    report = args.report
    send_email = args.email
    send_teams = args.teams
    today = args.today or date.today().strftime("%Y-%m-%d")
    print(f"[morning-check] 时间列表: {time_list}")
    print(f"[morning-check] 是否发送报告: {report}")
    print(f'[morning-check] 检查日期: {today}')
    _init_log(log_path / f"morning-check/{today}.log")
    # 业务逻辑写这里
    from utils import load_env
    from morning_check import MorningCheck
    load_env()
    _mc = MorningCheck(today=today, cache_db=SCRIPT_DIR / "cache_morning_check.db")
    for t in time_list:
        getattr(_mc, f"main_{t}")()
    if report:
        _mc.report()
    if send_email:
        _mc.report_to_mail()
    if send_teams:
        _mc.report_to_teams()


def handle_no_replay(args):
    """处理 no-replay 子命令"""
    send_report = args.report
    today = args.today or date.today().strftime("%Y-%m-%d")
    _init_log(log_path / f"no-reply-mails/{today}.log")
    logger.info(f"[no-replay] 是否发送报告: {send_report}")
    logger.info(f'[morning-check] 检查日期: {today}')
    # 业务逻辑写这里

    from no_reply import MailNotReply
    mn = MailNotReply(today=today)


def main():
    parser = argparse.ArgumentParser(prog="mail-check", description="mail check cli tool")
    subparsers = parser.add_subparsers(dest="command", required=True, help="子命令")

    # 子命令 morning-check
    parser_morning = subparsers.add_parser("morning-check", help="早上邮件检查")
    parser_morning.add_argument("times", nargs="+", help="时间参数，可选：0800 0818 0836 0901 0915")
    parser_morning.add_argument("-t", "--today", default=None, help="检查的日期")
    parser_morning.add_argument("-r", "--report", action="store_true", help="生成报告")
    parser_morning.add_argument("-e", "--email", action="store_true", help="发送报告到邮件")
    parser_morning.add_argument("-m", "--teams", action="store_true", help="发送报告到teams")

    parser_morning.set_defaults(func=handle_morning_check)

    # 子命令 no-replay
    parser_noreplay = subparsers.add_parser("no-replay", help="无回复检查")
    parser_noreplay.add_argument("-t", "--today", default=None, help="检查的日期")
    parser_noreplay.add_argument("-r", "--report", action="store_true", help="发送报告")
    parser_noreplay.set_defaults(func=handle_no_replay)

    parsed_args = parser.parse_args()
    parsed_args.func(parsed_args)


if __name__ == "__main__":
    main()
