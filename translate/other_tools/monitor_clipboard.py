#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : monitor_clipboard.py
@Author     : LeeCQ
@Date-Time  : 2025/12/6 01:06

监听剪切板，并将内容上传到feishu
"""
import io
import logging
import threading
import time
import typing
from datetime import datetime
from pathlib import Path
from zlib import adler32

from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import BINARY
from sqlalchemy import TEXT
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from PIL import BmpImagePlugin

from translate.tools import get_clipboard_content

if typing.TYPE_CHECKING:
    from translate.app import TranslationApp

logger = logging.getLogger("translate.other_tools.monitor_clipboard")

Base = declarative_base()


class ClipboardRecord(Base):
    __tablename__ = 'clipboard_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, default=datetime.now)
    typ = Column(String(10))
    text = Column(TEXT)
    data = Column(BINARY)


class MonitorClipboard:
    def __init__(self, app: "TranslationApp"):
        self.engine = None
        self.app = app
        self.started = False
        self.thread = None
        self._last_content = None

        self._init_database()

    def _init_database(self):
        """初始化数据库连接"""
        try:
            self.app.config.data_dir.mkdir(parents=True, exist_ok=True)
            db_path = Path(self.app.config.data_dir) / "clipboard_history.db"
            self.engine = create_engine(f'sqlite:///{db_path.as_posix()}')
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("clipboard_history Database initialized successfully")
        except Exception as e:
            logger.error(f"clipboard_history Error initializing database: {e}")
            raise e

    def _get_session(self):
        """获取数据库会话"""
        return self.Session()

    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            del self.Session
            logger.info("Database connection closed")

    def add_record(self, typ, text=None, data=None):
        session = self._get_session()
        try:
            record = ClipboardRecord(
                typ=typ,
                text=text,
                data=data
            )
            session.add(record)
            session.commit()
        except Exception as e:
            logger.error(f"Error adding record: {e}")
            raise e
        finally:
            session.close()

    def on_clipboard_change(self, typ, data):
        """剪切板内容发生变化时触发"""
        hash_value = self.hash_content(typ, data)
        if hash_value == self._last_content:
            return

        logger.info(f"Clipboard content changed: {typ} {data}")
        if typ == "text":
            self.add_record(typ, data)
        elif typ == "files":
            self.add_record(typ, "\n".join(data))
        elif typ == "image":
            if not isinstance(data, BmpImagePlugin.DibImageFile):
                raise ValueError(f"data[{type(data)}] is not a BmpImagePlugin.DibImageFile")
            ios = io.BytesIO()
            try:
                data.save(ios, format="png", quality=50, optimize=False)
                image = ios.getvalue()
                self.add_record(typ, text=str(adler32(image)), data=image)
            finally:
                ios.close()
        else:
            logger.error(f"Unknown clipboard type: {typ}")

        self._last_content = hash_value

    @staticmethod
    def hash_content(typ, data):
        """计算内容哈希值"""
        if typ == "text":
            return adler32(data.encode("utf-8"))
        elif typ == "files":
            return adler32("\n".join(data).encode("utf-8"))
        elif typ == "image":
            _t = io.BytesIO()
            data.save(_t, format="png", quality=50, optimize=False)
            image = _t.getvalue()
            _t.close()
            return adler32(image)
        else:
            logger.error(f"Unknown clipboard type: {typ}")
            return None

    def _run(self):
        logger.info(f"MonitorClipboard started")
        while True:
            if not self.started:
                break
            time.sleep(1)
            clipboard_data = get_clipboard_content()
            if clipboard_data[0] == "error":
                logger.error(f"Error during get clipboard content: {clipboard_data[1]}")
                continue
            self.on_clipboard_change(*clipboard_data)

    def start(self):
        """开启监听"""
        if self.started:
            return
        self.started = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """停止监听"""
        if not self.started:
            return
        self.started = False
        if self.thread:
            self.thread.join()
            self.thread = None
            logger.info(f"MonitorClipboard stopped")

    def is_running(self):
        """是否正在运行"""
        return self.started and self.thread and self.thread.is_alive()

    def get_records(self, typ=None, text=None, time_range: tuple[datetime, datetime] = None, page_size=50, page=1):
        session = self._get_session()
        try:
            query = session.query(ClipboardRecord)
            if typ:
                query = query.filter(ClipboardRecord.typ == typ)
            if text:
                query = query.filter(ClipboardRecord.text == text)
            if time_range and time_range[0] and time_range[1] and time_range[0] < time_range[1]:
                query = query.filter(ClipboardRecord.time.between(*time_range))
            query = query.order_by(ClipboardRecord.time.desc())
            query = query.limit(page_size).offset((page - 1) * page_size)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting records: {e}")
            raise e
        finally:
            session.close()

    def get_record_by_id(self, record_id):
        session = self._get_session()
        try:
            return session.query(ClipboardRecord).filter(ClipboardRecord.id == record_id).first()
        except Exception as e:
            logger.error(f"Error getting record by id: {e}")
            raise e
        finally:
            session.close()

    def clear_history(self, record_id=None):
        session = self._get_session()
        try:
            if record_id:
                session.query(ClipboardRecord).filter(ClipboardRecord.id == record_id).delete()
            else:
                session.query(ClipboardRecord).delete()
            session.commit()
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            raise e
        finally:
            session.close()
