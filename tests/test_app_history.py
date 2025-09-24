#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : test_app_history.py
@Author     : LeeCQ
@Date-Time  : 2025/9/23 23:00
"""
from pathlib import Path

import pytest
import os
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

# Import the module to test
from translate.app_history import (
    HistoryManager,
    TranslationRecord,
    Base,
    logger
)


class TestConfig:
    def __init__(self):
        self.translation_history_path = ":memory:"


@pytest.fixture
def history_manager():
    """Fixture to provide a HistoryManager instance with temp database"""
    config = TestConfig()
    with tempfile.TemporaryDirectory() as tmp:
        config.translation_history_path = Path(tmp) / "history.db"
        hm = HistoryManager(config)
        yield hm
        # Cleanup
        hm.close()


def test_initialization(history_manager):
    """Test database initialization"""
    assert history_manager.engine is not None
    assert history_manager.Session is not None
    assert os.path.exists(history_manager.config.translation_history_path)


def test_add_record(history_manager):
    """Test adding a translation record"""
    test_data = {
        'source_text': 'Hello',
        'translated_text': '你好',
        'source_lang': 'en',
        'target_lang': 'zh'
    }

    result = history_manager.add_record(**test_data)

    assert result['id'] is not None
    assert result['src'] == test_data['source_text']
    assert result['dst'] == test_data['translated_text']
    assert result['src_lang'] == test_data['source_lang']
    assert result['dst_lang'] == test_data['target_lang']


def test_add_record_failure(history_manager):
    """Test adding a record with database error"""
    with patch.object(history_manager, '_get_session') as mock_session:
        mock_session.return_value.commit.side_effect = SQLAlchemyError("DB Error")

        with patch.object(logger, 'error') as mock_logger:
            with pytest.raises(SQLAlchemyError):
                history_manager.add_record('test', '测试', 'en', 'zh')
            assert mock_logger.called


def test_get_all_records(history_manager):
    """Test retrieving all records"""
    # Add test records
    test_records = [
        ('Hello', '你好', 'en', 'zh'),
        ('World', '世界', 'en', 'zh'),
        ('Test', '测试', 'en', 'zh')
    ]

    for src, dst, sl, tl in test_records:
        history_manager.add_record(src, dst, sl, tl)

    records = history_manager.get_all_records()

    assert len(records) == 3
    assert records[0]['src'] == 'Test'  # Should be ordered by time desc
    assert records[1]['src'] == 'World'
    assert records[2]['src'] == 'Hello'


def test_get_all_records_empty(history_manager):
    """Test getting all records when empty"""
    records = history_manager.get_all_records()
    assert records == []


def test_get_all_records_failure(history_manager):
    """Test getting all records with database error"""
    with patch.object(history_manager, '_get_session') as mock_session:
        mock_session.return_value.query.side_effect = SQLAlchemyError("DB Error")

        with patch.object(logger, 'error') as mock_logger:
            result = history_manager.get_all_records()
            assert result == []
            assert mock_logger.called


def test_get_record_by_src(history_manager):
    """Test getting record by source text"""
    test_data = {
        'source_text': 'Unique text',
        'translated_text': '唯一文本',
        'source_lang': 'en',
        'target_lang': 'zh'
    }
    history_manager.add_record(**test_data)

    record = history_manager.get_record_by_src(test_data['source_text'])

    assert record is not None
    assert record['src'] == test_data['source_text']
    assert record['dst'] == test_data['translated_text']


def test_get_record_by_src_not_found(history_manager):
    """Test getting non-existent record by source text"""
    with patch.object(logger, 'warning') as mock_logger:
        record = history_manager.get_record_by_src('nonexistent')
        assert record is None
        assert mock_logger.called


def test_get_record_by_src_failure(history_manager):
    """Test getting record by source with database error"""
    with patch.object(history_manager, '_get_session') as mock_session:
        mock_session.return_value.query.side_effect = SQLAlchemyError("DB Error")

        with patch.object(logger, 'error') as mock_logger:
            result = history_manager.get_record_by_src('test')
            assert result is None
            assert mock_logger.called


def test_remove_record(history_manager):
    """Test removing a record by ID"""
    test_data = {
        'source_text': 'To be removed',
        'translated_text': '将被删除',
        'source_lang': 'en',
        'target_lang': 'zh'
    }
    added = history_manager.add_record(**test_data)

    result = history_manager.remove_record(added['id'])
    assert result is True

    # Verify it's gone
    assert history_manager.get_record_by_src(test_data['source_text']) is None


def test_remove_record_not_found(history_manager):
    """Test removing non-existent record"""
    with patch.object(logger, 'warning') as mock_logger:
        result = history_manager.remove_record(999)
        assert result is False
        assert mock_logger.called


def test_remove_record_failure(history_manager):
    """Test removing record with database error"""
    with patch.object(history_manager, '_get_session') as mock_session:
        mock_session.return_value.commit.side_effect = SQLAlchemyError("DB Error")

        with patch.object(logger, 'error') as mock_logger:
            result = history_manager.remove_record(1)
            assert result is False
            assert mock_logger.called


def test_clear_history(history_manager):
    """Test clearing all records"""
    # Add some records
    for i in range(5):
        history_manager.add_record(f'Text {i}', f'文本 {i}', 'en', 'zh')

    history_manager.clear_history()
    assert len(history_manager.get_all_records()) == 0


def test_clear_history_failure(history_manager):
    """Test clearing history with database error"""
    with patch.object(history_manager, '_get_session') as mock_session:
        mock_session.return_value.commit.side_effect = SQLAlchemyError("DB Error")

        with patch.object(logger, 'error') as mock_logger:
            history_manager.clear_history()
            assert mock_logger.called


def test_export_to_csv(history_manager):
    """Test exporting records to CSV"""
    # Add test records
    test_records = [
        ('Apple', '苹果', 'en', 'zh'),
        ('Banana', '香蕉', 'en', 'zh')
    ]

    for src, dst, sl, tl in test_records:
        history_manager.add_record(src, dst, sl, tl)

    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
        csv_path = tmp.name

    try:
        result = history_manager.export_to_csv(csv_path)
        assert result is True

        # Verify CSV content
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 3  # header + 2 records
            assert 'Apple,苹果,en,zh' in lines[1] or 'Apple,苹果,en,zh' in lines[2]
    finally:
        os.unlink(csv_path)


def test_export_to_csv_empty(history_manager):
    """Test exporting empty records to CSV"""
    with tempfile.NamedTemporaryFile(suffix='.csv') as tmp:
        result = history_manager.export_to_csv(tmp.name)
        assert result is True
