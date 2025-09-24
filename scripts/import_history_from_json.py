#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : import_history_from_json.py
@Author     : LeeCQ
@Date-Time  : 2025/9/24 16:32
"""
import logging
import json
from datetime import datetime

from translate.app_history import HistoryManager

logger = logging.getLogger(__name__)


def import_history_from_json(json_file_path: str, history_manager: HistoryManager):
    """从JSON文件导入翻译记录"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
            for record in records:
                record["record_time"] = datetime.fromisoformat(record.pop("time"))
                history_manager.add_record(**record)
        logger.info(f"Imported {len(records)} records from {json_file_path}")
    except Exception as e:
        logger.error(f"Error importing from JSON: {e}")


if __name__ == '__main__':
    import logging
    from translate.config import config as _c

    logging.basicConfig(level=logging.DEBUG)

    history_manager = HistoryManager(_c)
    import_history_from_json('.translate/translation_history.json', history_manager)
