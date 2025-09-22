#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : app_history.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:18
"""
import json
import csv
import os
from datetime import datetime
from logging import getLogger


logger = getLogger("translate.app.history")


class HistoryManager:
    def __init__(self, config):
        self.config = config
        self.history = []
        self.load_history()

    def load_history(self):
        try:
            if self.config.translation_history_path and \
                    os.path.exists(self.config.translation_history_path):
                with open(self.config.translation_history_path, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                logger.info(f"Loaded {len(self.history)} translation records")
        except Exception as e:
            logger.error(f"Error loading translation history: {e}")
            self.history = []

    def save_history(self):
        try:
            if self.config.translation_history_path:
                with open(self.config.translation_history_path, 'w', encoding='utf-8') as f:
                    json.dump(self.history, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved {len(self.history)} translation records")
        except Exception as e:
            logger.error(f"Error saving translation history: {e}")

    def add_record(self, source_text, translated_text, source_lang, target_lang):
        record = {
            'time': datetime.now().isoformat(),
            'src': source_text,
            'dst': translated_text,
            'src_lang': source_lang,
            'dst_lang': target_lang
        }
        self.history.append(record)
        self.save_history()
        return record

    def remove_record(self, record):
        self.history.remove(record)
        self.save_history()

    def clear_history(self):
        self.history = []
        self.save_history()
        logger.info("Translation history cleared")

    def export_to_csv(self, file_path):
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['time', 'src', 'dst', 'src_lang', 'dst_lang'])
                for record in self.history:
                    writer.writerow([
                        record['time'],
                        record['src'],
                        record['dst'],
                        record['src_lang'],
                        record['dst_lang']
                    ])
            logger.info(f"Exported {len(self.history)} records to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False
