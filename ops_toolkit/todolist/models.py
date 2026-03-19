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
from typing import Iterable

from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import or_, desc, asc
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from ops_toolkit.tools import toolkit_notify

logger = logging.getLogger("ops_toolkit.todolist.models")
Base = declarative_base()

map_status_to_emoji = {
    0: "🔄",
    1: "🎉",
    2: "❌",
}

map_status_to_int = {
    "进行中": 0,
    "已完成": 1,
    "已取消": 2,
}
map_int_to_status = {v: k for k, v in map_status_to_int.items()}


def json_serializer(obj):
    if isinstance(obj, (datetime,)):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    raise TypeError(f"Object of type '{obj.__class__.__name__}' is not JSON serializable")


class TaskStatus:
    UNDO = 0
    DONE = 1
    DELETE = 2


class BaseModel(Base):
    __abstract__ = True

    def to_dict(self):
        # self.__table__.columns: set
        return {c.name: getattr(self, c.name) for c in set(self.__table__.columns)}


class TodolistTaskModel(BaseModel):
    __tablename__ = 'todolist_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, comment="标题")
    desc = Column(Text, nullable=True, comment="描述")
    create_time = Column(DateTime, default=datetime, comment="创建时间")
    do_time = Column(DateTime, nullable=True, comment="计划做的时间")
    link = Column(String(500), nullable=True, comment="关联链接")
    status = Column(Integer, default=0, comment="0: 未完成 1: 已完成 2: 删除")
    work_time_occupied = Column(Integer, default=0, comment="占用时长（min）")

    def status_string(self):
        return map_int_to_status.get(self.status, "未知")

    def status_emoji(self):
        return map_status_to_emoji.get(self.status, "")

    def set_status(self, status):
        self.status = map_status_to_int.get(status, 0)


class TodolistHistoryModel(BaseModel):
    __tablename__ = 'todolist_history'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tid = Column(Integer, ForeignKey('todolist_tasks.id'), comment="task ID")
    c_time = Column(DateTime, default=datetime.now, comment="修改时间")
    c_table = Column(String(255), nullable=False, comment="修改表")
    c_key = Column(String(255), nullable=False, comment="修改字段")
    c_value = Column(Text, nullable=True, comment="修改值")
    # change = Column(Text, nullable=False, comment="修改内容")  # JSON format string


class TodolistConfigModel(BaseModel):
    __tablename__ = 'todolist_config'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(255), nullable=False, index=True, comment="配置项")
    value = Column(Text, nullable=True, comment="配置值")


class DayShift(BaseModel):
    __tablename__ = 'day_shifts'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(String(9), index=True, comment="日期: YYYY-mm-dd")
    shift = Column(String(255), nullable=False, comment="班次：night|day|mid")
    day_type = Column(String(255), nullable=False, comment="日期类型：工作日|节假日|带薪节假日")


class DBManager:

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
            self._update_tables()
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("todolist Database initialized successfully")
        except Exception as e:
            logger.error(f"todolist Error initializing database: {e}")
            raise e

    def _update_tables(self):
        session = sessionmaker(self.engine)()
        try:
            if session.execute(text(
                    """SELECT MAX(CASE WHEN name = 'todolist' THEN 1 ELSE 0 END)       AS todolist_exists,
                              MAX(CASE WHEN name = 'todolist_tasks' THEN 1 ELSE 0 END) AS tasks_exists
                       FROM sqlite_master
                       WHERE type = 'table'
                         AND name IN ('todolist', 'todolist_tasks');
                    """
            )).first() == (1, 0):
                session.execute(text("ALTER TABLE todolist RENAME TO todolist_tasks;"))
                session.commit()

            _t_names = [t[1] for t in session.execute(text("PRAGMA table_info(todolist_history)")).all()]
            if "change" in _t_names and "t_key" not in _t_names and "t_table" not in _t_names:
                session.execute(text("DROP TABLE todolist_history;"))
                session.commit()

        except Exception as e:
            logger.error(f"todolist Error updating tables: {e}")
            session.rollback()
        finally:
            session.close()

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
    def add_task(
            self,
            title,
            details="",
            link="",
            do_time: datetime = None,
            status: str | int = 0
    ) -> TodolistTaskModel:
        """

        :param title:
        :param details: 描述
        :param link:
        :param do_time:
        :param status:
        :return:
        """
        if do_time is None:
            do_time = datetime.now() + timedelta(hours=1)

        session = self._get_session()
        try:
            record = TodolistTaskModel(
                title=title,
                desc=details,
                link=link,
                create_time=datetime.now(),
                do_time=do_time,
                status=map_status_to_int.get(status, 0) if isinstance(status, str) else 0,
            )
            session.add(record)
            session.commit()
            toolkit_notify("todolist", f"添加任务成功: {title} \n {do_time}")
            logger.info(f"todolist Record added: {record.id}")
            return record
        except Exception as e:
            logger.error(f"todolist Error adding record: {e}")
            session.rollback()
            raise e
        finally:
            session.close()

    def update_task(self, tid, **kwargs):
        """title="", desc="", link="", do_time: datetime = None

        :param tid:
        :param kwargs:
        :return:
        """
        session = self._get_session()
        if "status" in kwargs and isinstance(kwargs["status"], str):
            kwargs["status"] = map_status_to_int.get(kwargs["status"], 0)
        try:
            record = session.query(TodolistTaskModel).filter(TodolistTaskModel.id == tid).first()
            if record:
                old = {k: getattr(record, k) for k in kwargs.keys() if getattr(record, k) != kwargs[k]}
                [setattr(record, key, kwargs[key]) for key in old.keys()]
                change = {k: [v, kwargs[k]] for k, v in old.items() if old[k] != kwargs[k]}
                for k, v in change.items():
                    session.add(TodolistHistoryModel(
                        tid=tid,
                        c_table="todolist_tasks",
                        c_key=k,
                        c_value=json.dumps(v, ensure_ascii=False, default=json_serializer)
                    ))
                session.flush()
                session.commit()
                c_s = "\n".join(f"{k}: {v[0]} -> {v[1]}" for k, v in change.items())
                toolkit_notify("todolist", f"更新任务成功: {tid} : {record.title} \n{c_s}")
                logger.info(f"create history: {change}")
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

    def top_10_task(self) -> list[type[TodolistTaskModel] | TodolistTaskModel]:
        """获取10条未完成的任务"""
        session = self._get_session()
        try:
            return session.query(TodolistTaskModel).filter(TodolistTaskModel.status == 0) \
                .order_by(TodolistTaskModel.do_time).limit(10).all()
        except Exception as e:
            logger.error(f"todolist Error getting top 10 todo: {e}")
            return []
        finally:
            session.close()

    def get_task(self, tid) -> type[TodolistTaskModel] | TodolistTaskModel | None:
        """获取一个待办事项"""
        session = self._get_session()
        try:
            return session.query(TodolistTaskModel).filter(TodolistTaskModel.id == tid).first()
        except Exception as e:
            logger.error(f"todolist Error getting todo {tid=}: {e}")
            return None
        finally:
            session.close()

    def query_task(
            self,
            query: str,
            order_bys: list[tuple[str, str]] = None
    ) -> Iterable[type[TodolistTaskModel] | TodolistTaskModel]:
        """查询待办事项

        :param query:
        :param order_bys: list[tuple[name, desc/asc]]
        :return:
        """
        session = self._get_session()
        order_bys = order_bys or []
        try:
            order_bys = [
                desc(getattr(TodolistTaskModel, name)) if order == "desc" else asc(getattr(TodolistTaskModel, name))
                for name, order in order_bys
            ]

            return session.query(TodolistTaskModel).filter(
                or_(
                    TodolistTaskModel.title.like(f"%{query}%"),
                    TodolistTaskModel.desc.like(f"%{query}%"),
                )
            ).order_by(*order_bys)
        except Exception as e:
            logger.error(f"todolist Error querying todo {query=}: {e}")
            return []
        finally:
            session.close()

    def complete_task(self, tid, status: int = 1):
        """完成待办事项"""
        return self.update_task(tid, status=status)

    def get_setting(self, key, default: str = None) -> str:
        """从设置表中获取一个值.
        如果key不存在且default=None, 则KeyError
        """
        session = self._get_session()
        try:
            req = session.query(TodolistConfigModel).filter(TodolistConfigModel.key == key).first()
            if req is not None:
                return str(req.value)
            if default is not None:
                logger.warning(f'"{key}" not in table "todolist_config", using default: "{default}"')
                return default
            logger.error(f'"{key}" not in table "todolist_config", and default is None')
            raise KeyError(f'"{key}" not in table "todolist_config", and default is None')

        finally:
            session.close()

    def set_setting(self, key: str, value: str):
        """设置一个值"""
        session = self._get_session()
        try:
            req = session.query(TodolistConfigModel).filter(TodolistConfigModel.key == key).first()
            if req is not None:
                req.value = value
            else:
                req = TodolistConfigModel(key=key, value=value)
                session.add(req)
            session.commit()
            logger.info(f'todolist_config "{key}" updated:  {value}')
            return True
        except Exception as e:
            logger.error(f"Error updating todolist_config {key=}: {e}")
            session.rollback()
            raise e
        finally:
            session.close()

    def set_day_shift(self, date: str | datetime, shift, day_type):
        """设置班次信息"""
        session = self._get_session()
        date = date if isinstance(date, str) else date.strftime("%Y-%m-%d")
        try:
            req = session.query(DayShift).filter(DayShift.date == date).first()
            if req is not None:
                req.shift = shift
                req.day_type = day_type
            else:
                req = DayShift(date=date, shift=shift, day_type=day_type)
                session.add(req)
            session.commit()
        except Exception as e:
            logger.error(f"Error updating todolist_config {date=}: {e}")
            raise e
        finally:
            session.close()

    def get_day_shift(self, date: str | datetime):
        """获取班次信息
        :param date: 日期字符串 YYYY-mm-dd
        """
        session = self._get_session()
        if not isinstance(date, str):
            date = date.strftime("%Y-%m-%d")
        try:
            req = session.query(DayShift).filter(DayShift.date == date).first()
            if req is not None:
                return req.shift, req.day_type
            return None, None
        except Exception as e:
            logger.error(f"Error updating todolist_config {date=}: {e}")
            return None, None
        finally:
            session.close()


if __name__ == '__main__':
    from ops_toolkit.config import config


    class _APP:
        def __init__(self):
            self.config = config


    db = DBManager(_APP())
    print(db.get_setting("test", "000"))
