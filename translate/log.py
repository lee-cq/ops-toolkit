import logging
import logging.config

from translate import DEBUGGER
from translate.config import config


class DebugInfoFilter(logging.Filter):
    """日志过滤器：当级别为DEBUG时附加debug字段信息到msg"""

    def filter(self, record):
        # 检查当前日志级别是否为DEBUG
        if record.levelno == logging.DEBUG:
            # 检查record是否包含debug字段
            if hasattr(record, 'debug'):
                # 将debug字段内容附加到msg
                record.msg = f"{record.msg} [Debug Info: {record.debug}]"
        # 始终返回True以允许日志记录通过
        return True


def init_logger():
    """初始化日志配置"""
    logging.config.dictConfig(
        {
            'version':    1,
            # 'disable_existing_loggers': False,
            'formatters': {
                'translate_formatter': {
                    'format':  '%(asctime)s - [%(process)d: %(thread)d] %(filename)s - [%(levelname)s] - %(message)s',  # 包含时间、logname、等级、msg
                    'datefmt': '%Y-%m-%d %H:%M:%S'  # 时间格式
                },
                'row_request':         {
                    'format':  '[%(asctime)s] - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'  # 时间格式
                }
            },
            'handlers':   {
                'console_handler':         {
                    'class':     'logging.StreamHandler',  # 控制台输出
                    'formatter': 'translate_formatter',
                    'level':     'DEBUG'  # 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
                },
                'file_handler':            {
                    'class':     'logging.FileHandler',  # 文件输出
                    'filename':  config.log_path,  # 日志文件名
                    'formatter': 'translate_formatter',
                    'level':     'INFO',  # 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
                    "encoding":  "utf-8"
                },
                "file_debug_handler":      {
                    'class':     'logging.FileHandler',
                    'formatter': 'translate_formatter',
                    'level':     'DEBUG',
                    "encoding":  "utf-8",
                    'filename':  f"{config.log_path.with_suffix('.debug.log')}"
                },
                "row_request_handler":     {
                    'class':     'logging.handlers.RotatingFileHandler',
                    'formatter': 'row_request',
                    'level':     'DEBUG',
                    'filename':  f"{config.log_path.with_suffix('.row_request.log')}",
                },
                "keepalive_handler":       {
                    'class':     'logging.FileHandler',
                    'formatter': 'translate_formatter',
                    'level':     'DEBUG',
                    "encoding":  "utf-8",
                    'filename':  f"{config.log_path.with_suffix('.keepalive.log')}"
                },
                "hourly_reminder_handler": {
                    'class':     'logging.FileHandler',
                    'formatter': 'translate_formatter',
                    'level':     'DEBUG',
                    "encoding":  "utf-8",
                    'filename':  f"{config.log_path.with_suffix('.hourly_reminder.log')}"
                }
            },
            "filters":    {},
            'loggers':    {
                'translate':                 {  # 指定translate日志器
                    'handlers':  ['console_handler', 'file_handler', "file_debug_handler"],
                    'level':     'DEBUG',
                    'propagate': True  # 不向上传播日志
                },
                'translate.row_request':     {
                    'handlers':  ['row_request_handler', 'console_handler'],
                    'level':     'DEBUG',
                    'propagate': False
                },
                'translate.keepalive':       {
                    'handlers':  ['keepalive_handler'],
                    'level':     'DEBUG',
                    'propagate': True,
                },
                'translate.hourly_reminder': {
                    'handlers':  ['hourly_reminder_handler'],
                    'level':     'DEBUG',
                    'propagate': True,
                }
            }
        }
    )
