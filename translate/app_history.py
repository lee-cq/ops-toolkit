#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : app_history.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:18
"""
import csv
from pathlib import Path
from datetime import datetime
from logging import getLogger

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

logger = getLogger("translate.app.history")

Base = declarative_base()


class TranslationRecord(Base):
    __tablename__ = 'translation_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, default=datetime.now)
    src = Column(Text)
    dst = Column(Text)
    src_lang = Column(String(10))
    dst_lang = Column(String(10))


class HistoryManager:
    def __init__(self, config):
        self.config = config
        self.engine = None
        self.Session: sessionmaker
        self._initialize_database()

    def _initialize_database(self):
        """初始化数据库连接"""
        try:
            db_path = Path(self.config.translation_history_path or 'translation_history.db')
            # 确保路径存在
            db_path.parent.mkdir(parents=True, exist_ok=True)

            self.engine = create_engine(f'sqlite:///{db_path.as_posix()}')
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise e

    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            del self.Session
            logger.info("Database connection closed")

    def _get_session(self):
        """获取数据库会话"""
        return self.Session()

    def add_record(self, src: str, dst: str, src_lang: str, dst_lang: str, record_time: datetime = None):
        """添加翻译记录"""
        session = self._get_session()
        try:
            record = TranslationRecord(
                time=record_time or datetime.now(),
                src=src,
                dst=dst,
                src_lang=src_lang,
                dst_lang=dst_lang
            )
            session.add(record)
            session.commit()
            logger.info("Translation record added successfully")
            return {
                'id':       record.id,
                'time':     record.time.isoformat(),
                'src':      record.src,
                'dst':      record.dst,
                'src_lang': record.src_lang,
                'dst_lang': record.dst_lang
            }
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding translation record: {e}")
            raise
        finally:
            session.close()

    def get_all_records(self):
        """获取所有翻译记录"""
        session = self._get_session()
        try:
            records = session.query(TranslationRecord).order_by(TranslationRecord.time.desc()).all()
            return records
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving translation records: {e}")
            return []
        finally:
            session.close()

    def query_by_id(self, record_id: int) -> list[type[TranslationRecord]]:
        session = self._get_session()
        try:
            return session.query(TranslationRecord).where(TranslationRecord.id > record_id).all()
        finally:
            session.close()

    def get_record_by_src(self, src: str) -> dict:
        """根据源文本获取记录"""
        session = self._get_session()
        try:
            record = session.query(TranslationRecord).filter(TranslationRecord.src == src).first()
            if record:
                return {
                    'id':       record.id,
                    'time':     record.time.isoformat(),
                    'src':      record.src,
                    'dst':      record.dst,
                    'src_lang': record.src_lang,
                    'dst_lang': record.dst_lang
                }
            else:
                logger.warning(f"Record with source text {src} not found")
                return {}
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving translation record by source text: {e}")
            return {}
        finally:
            session.close()

    def remove_record(self, record_id):
        """根据ID删除记录"""
        session = self._get_session()
        try:
            record = session.query(TranslationRecord).filter(TranslationRecord.id == record_id).first()
            if record:
                session.delete(record)
                session.commit()
                logger.info(f"Record {record_id} removed successfully")
                return True
            else:
                logger.warning(f"Record {record_id} not found")
                return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error removing translation record: {e}")
            return False
        finally:
            session.close()

    def clear_history(self):
        """清空所有历史记录"""
        session = self._get_session()
        try:
            session.query(TranslationRecord).delete()
            session.commit()
            logger.info("Translation history cleared")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error clearing translation history: {e}")
        finally:
            session.close()

    def export_to_csv(self, file_path):
        """导出记录到CSV文件"""
        try:
            records = self.get_all_records()
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'time', 'src', 'dst', 'src_lang', 'dst_lang'])
                for record in records:
                    writer.writerow([
                        record.id,
                        record.time.isoformat(),
                        record.src,
                        record.dst,
                        record.src_lang,
                        record.dst_lang
                    ])
            logger.info(f"Exported {len(records)} records to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False


if __name__ == '__main__':
    import logging
    from translate.config import config as _c

    logging.basicConfig(level=logging.DEBUG)

    history_manager = HistoryManager(_c)
