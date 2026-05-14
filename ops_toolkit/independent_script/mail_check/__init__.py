#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : mail_check.py
@Author     : LeeCQ
@Date-Time  : 2026/4/12 01:06

监听剪切板
"""

import imaplib
import datetime
import email
import json
from email.header import decode_header
from email.utils import parseaddr
from pathlib import Path


class TradeDate:

    def __init__(self, date_: datetime.date = None):
        # 今天日期
        self.current = date_ or datetime.date.today()

        # A 股 / 港股 是否为节假日
        self.is_holiday_hk = False  # 港股：True = 休市
        self.is_holiday_cn = True  # A 股：True = 休市

        # 上一个交易日
        self.last_date_hk = None
        self.last_date_cn = None

        # 初始化自动获取
        self.update_status()

    def update_status(self):
        _year = self.current.strftime("%Y")
        _fhs = json.loads(Path(__file__).parent.joinpath(f"holiday_{_year}").read_text(encoding="utf-8"))

        if self.current.weekday() > 5:
            self.is_holiday_hk = True
            self.is_holiday_cn = True
        else:
            _ds = self.current.strftime("%Y-%m-%d")
            self.is_holiday_hk = _ds in _fhs["hk"]
            self.is_holiday_cn = _ds in _fhs["cn"]

        self.last_date_hk = self.get_last_trade_date(self.current - datetime.timedelta(days=1), _fhs["hk"])
        self.last_date_cn = self.get_last_trade_date(self.current - datetime.timedelta(days=1), _fhs["cn"])

    def get_last_trade_date(self, date: datetime.date, holidays: list[str]):
        if date.weekday() > 5 or date.strftime("%Y-%m-%d") in holidays:
            return self.get_last_trade_date(date - datetime.timedelta(days=1), holidays)
        return date


class MailBox(object):
    def __init__(self, server, user, password, **kwargs):
        self.server = server
        self.user = user
        self.password = password

        self.box = imaplib.IMAP4(self.server)
        self.box.login(self.user, self.password)

    def __del__(self):
        """析构函数：自动登出，释放连接"""
        try:
            self.box.logout()
        except:
            pass

    @staticmethod
    def _decode_str(s):
        """解码邮件标题/内容，解决乱码问题"""
        value, charset = decode_header(s)[0]
        if charset:
            value = value.decode(charset, errors="ignore")
        return value

    def find(self, date, keywords, box="INBOX"):
        """
        搜索邮件
        :param date: 日期，格式 "01-Jan-2025" 或 datetime.date
        :param keywords: 关键词列表，如 ["订单", "发票"]
        :param box: 邮箱文件夹，默认 INBOX 收件箱
        :return: 匹配到的邮件ID列表
        """
        # 选择邮箱文件夹
        self.box.select(box)

        # 处理日期格式
        if isinstance(date, datetime.date):
            date = date.strftime("%d-%b-%Y")

        # 拼接搜索条件：日期 + 包含所有关键词
        criterion = f'(ON "{date}"'
        for kw in keywords:
            criterion += f' BODY "{kw}"'
        criterion += ")"

        # 执行搜索
        typ, data = self.box.search(None, criterion)
        mail_ids = data[0].split()  # 转成ID列表

        return [mid.decode() for mid in mail_ids]

    def get_mail(self, mail_id):
        """
        根据邮件ID获取完整邮件信息
        :param mail_id: 邮件ID
        :return: 字典格式邮件信息
        """
        # 读取原始邮件
        typ, data = self.box.fetch(mail_id, "(RFC822)")
        raw_email = data[0][1]

        # 解析邮件
        msg = email.message_from_bytes(raw_email)

        # 解析基础信息
        subject = self._decode_str(msg["Subject"])
        from_addr = self._decode_str(parseaddr(msg.get("From", ""))[1])
        to_addr = self._decode_str(parseaddr(msg.get("To", ""))[1])
        date_str = msg.get("Date", "")

        # 解析邮件正文
        body = ""
        attachments = []

        if msg.is_multipart():
            # 多部分邮件（正文+附件）
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition"))

                # 正文
                if content_type == "text/plain" and "attachment" not in disposition:
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except:
                        body = part.get_payload(decode=True).decode("gbk", errors="ignore")

                # 附件
                if "attachment" in disposition:
                    filename = self._decode_str(part.get_filename())
                    attachments.append(filename)
        else:
            # 纯文本邮件
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except:
                body = msg.get_payload(decode=True).decode("gbk", errors="ignore")

        return {
            "id": mail_id,
            "主题": subject,
            "发件人": from_addr,
            "收件人": to_addr,
            "时间": date_str,
            "正文": body.strip(),
            "附件": attachments
        }
