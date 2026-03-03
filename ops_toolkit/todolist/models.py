#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : models.py
@Author     : LeeCQ
@Date-Time  : 2026/2/5 00:57
"""
import json
import logging
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from ops_toolkit.tools import toolkit_notify

logger = logging.getLogger("ops_toolkit.todolist.models")
Base = declarative_base()


def json_serializer(obj):
    if isinstance(obj, (datetime,)):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    raise TypeError(f"Object of type '{obj.__class__.__name__}' is not JSON serializable")


class TodolistModel(Base):
    __tablename__ = 'todolist'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, comment="标题")
    desc = Column(Text, nullable=True, comment="描述")
    create_time = Column(DateTime, default=datetime, comment="创建时间")
    do_time = Column(DateTime, nullable=True, comment="计划做的时间")
    link = Column(String(500), nullable=True, comment="关联链接")
    status = Column(Integer, default=0, comment="0: 未完成 1: 已完成 2: 删除")
    work_time_occupied = Column(Integer, default=0, comment="占用时长（min）")


class TodolistHistoryModel(Base):
    __tablename__ = 'todolist_history'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tid = Column(Integer, ForeignKey('todolist.id'), comment="todolistID")
    create_time = Column(DateTime, default=datetime, comment="修改时间")
    change = Column(Text, nullable=False, comment="修改内容")  # JSON format string
    # t_key = Column(String(255), nullable=False, comment="修改字段")
    # old_value = Column(Text, nullable=True, comment="旧值")
    # new_value = Column(Text, nullable=True, comment="新值")


class TodolistManager:

    def __init__(self, app):
        self.engine = None
        self.app = app
        self.started = False
        self.thread = None
        self._last_content = None
        self.auto_sls_split = False

        self._init_database()

    def _init_database(self):
        """初始化数据库连接"""
        try:
            self.app.config.data_dir.mkdir(parents=True, exist_ok=True)
            db_path = Path(self.app.config.data_dir) / "todolist.db"
            self.engine = create_engine(f'sqlite:///{db_path.as_posix()}')
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("todolist Database initialized successfully")
        except Exception as e:
            logger.error(f"todolist Error initializing database: {e}")
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
            logger.info("todolist Database connection closed")

    # 添加记录
    def add_record(self, title, desc="", link="", do_time: datetime = None):
        """"""
        if do_time is None:
            do_time = datetime.now() + timedelta(hours=1)

        session = self._get_session()
        try:
            record = TodolistModel(
                title=title,
                desc=desc,
                link=link,
                create_time=datetime.now(),
                do_time=do_time
            )
            session.add(record)
            session.commit()
            toolkit_notify("todolist", f"添加任务成功: {title} \n {do_time}")
            logger.info(f"todolist Record added: {record.id}")
            return record.id
        except Exception as e:
            logger.error(f"todolist Error adding record: {e}")
            session.rollback()
            raise e
        finally:
            session.close()

    def update_record(self, tid, **kwargs):
        """title="", desc="", link="", do_time: datetime = None

        :param tid:
        :param kwargs:
        :return:
        """
        session = self._get_session()
        try:
            record = session.query(TodolistModel).filter(TodolistModel.id == tid).first()
            if record:
                old = {k: getattr(record, k) for k in kwargs.keys()}
                [setattr(record, key, value) for key, value in kwargs.items()]
                logger.debug(f"todolist New Record: {record.__dict__}")
                change = {
                    "old": old,
                    "new": kwargs
                }
                session.add(TodolistHistoryModel(
                    tid=tid,
                    create_time=datetime.now(),
                    change=json.dumps(change, ensure_ascii=False, default=json_serializer)
                ))
                session.flush()
                session.commit()

                toolkit_notify("todolist", f"更新任务成功: {tid=} ")
                logger.debug(f"create history: {change}")
                logger.info(f"todolist Record updated: {tid=}")
                session.flush()
            else:
                logger.error(f"todolist Record not found: {tid=}")
                raise ValueError("todolist Record not found")
        except ValueError:
            pass
        except Exception as e:
            logger.error(f"todolist Error updating record: {e}")
            session.rollback()
            raise e

        finally:
            session.close()

    def top_10_todo(self) -> list[type[TodolistModel]]:
        """获取10条未完成的任务"""
        session = self._get_session()
        try:
            return session.query(TodolistModel).filter(TodolistModel.status == 0) \
                .order_by(TodolistModel.do_time).limit(10).all()
        except Exception as e:
            logger.error(f"todolist Error getting top 10 todo: {e}")
            return []
        finally:
            session.close()

    def complete_todo(self, tid) -> bool:
        """完成待办事项"""
        try:
            self.update_record(tid, status=1)
            logger.info("任务 {tid} 已经完成")
            toolkit_notify("todolist", f"任务 {tid} 已经完成")
            return True
        except Exception as e:
            logger.error(f"todolist Error completing todo {tid=}: {e}")
            toolkit_notify("todolist", f"任务 {tid} 完成失败\n{e}")
            return False
