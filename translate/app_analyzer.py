#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : app_analyzer.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:21
"""
from logging import getLogger
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

logger = getLogger("translate.app.analyzer")

# 确保nltk资源可用
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')

except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('punkt_tab')


# def find_nltk(name: str):
#     try:
#         nltk.data.find(name)
#     except LookupError:
#         nltk.download(name.split('/')[-1])
#
#
# for name in ('tokenizers/punkt', 'corpora/stopwords'):
#     find_nltk(name)
#

class TextAnalyzer:
    def __init__(self, history_manager):
        self.history_manager = history_manager
        self.word_counts = {}

    def analyze_translations(self):
        """分析翻译历史，提取高频词汇"""
        self.word_counts = {}

        # 收集所有源文本
        all_source_texts = [record['src'] for record in self.history_manager.history]

        # 处理英文文本
        english_stopwords = set(stopwords.words('english'))
        english_words = []

        for text in all_source_texts:
            # 简单判断是否为英文文本
            if re.match(r'^[a-zA-Z\s,.!?\'"]+$', text.strip()):
                words = word_tokenize(text.lower())
                # 过滤停用词和非字母字符
                filtered_words = [word for word in words if word.isalpha() and word not in english_stopwords]
                english_words.extend(filtered_words)

        # 计算词频
        if english_words:
            self.word_counts['english'] = Counter(english_words)

        logger.info(
            f"Completed text analysis. Found {sum(len(counts) for counts in self.word_counts.values())} unique words.")
        return self.word_counts

    def export_word_list(self, lang, file_path, min_frequency=1):
        """导出单词表到TXT文件"""
        if lang not in self.word_counts:
            return False

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for word, count in self.word_counts[lang].most_common():
                    if count >= min_frequency:
                        f.write(f"{word}\n")

            logger.info(f"Exported {len(self.word_counts[lang])} words to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting word list: {e}")
            return False
