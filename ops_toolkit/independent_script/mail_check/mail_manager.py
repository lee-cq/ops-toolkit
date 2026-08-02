#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : mail_manager
@Author     : LeeCQ
@Date-Time  : 2026/7/30


"""
import logging
import imaplib
import re
import sqlite3
import email
import email.header
import email.utils
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import base64
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("mail_check.mail_manager")
imaplib.Debug = 5


def date_to_imap_str(dt_str: str):
    """yyyy-MM-dd → IMAP日期格式 DD-Mon-YYYY"""
    dt = datetime.strptime(dt_str, "%Y-%m-%d")
    return dt.strftime("%d-%b-%Y")


def get_imap(host, port, user, password, ssl=True) -> imaplib.IMAP4_SSL | imaplib.IMAP4:
    if ssl:
        _imap = imaplib.IMAP4_SSL(host, port)
    else:
        _imap = imaplib.IMAP4(host, port)

    _status, data = _imap.login(user, password)
    if _status == 'OK':
        logger.info(f"IMAP: {host}:{port} [{ssl=}] {user} 登录成功 .")
    else:
        logger.error(f"IMAP: {host}:{port} [{ssl=}] {user} 登录失败 .")
        raise ValueError(f"IMAP: {host}:{port} [{ssl=}] {user} 登录失败: {data}")
    return _imap


@dataclass
class Mail:
    # uid, mail_id, subject, send_time, sender, body, attachments
    uid: str | None
    mail_id: str
    subject: str
    send_time: datetime | None
    sender: str
    body: dict
    attachments: Dict[str, str]

    def list_attachments(self):
        return tuple(self.attachments.keys())

    def get_attachment(self, name=None) -> bytes:
        if name is None:
            name = self.list_attachments()[0]
        return base64.b64decode(self.attachments[name])

    def get_text(self):
        return self.body.get("text")

    def get_html(self):
        return self.body.get("html")

    def get_send_time(self):
        if isinstance(self.send_time, str):
            _ = self.send_time.split('+')
        return datetime.strptime(_[0], '%Y-%m-%d %H:%M:%S')

    @classmethod
    def default(cls):
        return cls(uid=None, mail_id="", subject="", send_time=datetime.now(), sender="", body={}, attachments={})

    def to_dict(self):
        return {
            "uid": self.uid,
            "mail_id": self.mail_id,
            "subject": self.subject,
            "send_time": self.send_time,
            "sender": self.sender,
            "body": self.body,
            "attachments": self.attachments
        }


class MailManager:

    def __init__(
            self,
            imap: imaplib.IMAP4 | imaplib.IMAP4_SSL = None,
            cache_db=None,
    ):
        self.sqlite_adapter()
        self.db = sqlite3.connect(cache_db or "./mail_manager.db", detect_types=sqlite3.PARSE_DECLTYPES)
        self.db.row_factory = sqlite3.Row
        self.init_db()
        self.imap = imap

    def sqlite_adapter(self):
        """"""
        sqlite3.register_adapter(dict, lambda d: json.dumps(d))
        sqlite3.register_converter("JSON", json.loads)

    def init_db(self):
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS mails ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " uid TEXT NOT NULL UNIQUE,"
            " mail_id Text unique,"
            " subject Text not null,"
            " send_time DateTime not null,"
            " sender text not null,"
            " body Text not null, "
            " attachments JSON "
            " )"
        )
        self.db.commit()

    def insert_mail(self, uid, mail_id, subject, send_time, sender, body, attachments=None, **kwargs):
        """缓存邮件"""
        if attachments:
            attachments = {
                k: base64.encodebytes(v).decode("ascii") for k, v in attachments.items()
            }
        try:
            self.db.execute(
                "INSERT INTO `mails` "
                "(uid, mail_id, subject, send_time, sender, body, attachments) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uid, mail_id, subject, send_time, sender, body, json.dumps(attachments))
            )
            self.db.commit()
        except sqlite3.IntegrityError as _e:
            logger.warning(f"主键冲突: {_e}")

    def search_email(self, subject, time_start: datetime | str, time_end: datetime | str, /,
                     folder="inbox",
                     force_imap=False,
                     **kwargs
                     ) -> Mail:
        """从缓存数据库中查询邮件，如果没找到去imap中找

        :param force_imap:
        :param subject:
        :param time_start:
        :param time_end:
        :param folder:
        :return:
        """
        if isinstance(time_start, str) and isinstance(time_end, str):
            if len(time_start) != len(time_end) and (len(time_start) not in (5, 10, 16)):
                raise ValueError("time_start and time_end 长度必须相同, 并且长度必须是5(01:01) / 16(2026-01-01 01:01)")
            if len(time_start) > 9 and time_end < time_start:
                raise ValueError("指定日期时，time_end必须大于time_start")
            if len(time_start) == 5:
                today = datetime.today().strftime("%Y-%m-%d ")
                time_start = datetime.strptime(today + time_start, "%Y-%m-%d %H:%M")
                time_end = datetime.strptime(today + time_end, "%Y-%m-%d %H:%M")
                if time_start > time_end:
                    time_start = time_start - timedelta(days=1)
            elif len(time_start) == 16:
                time_start = datetime.strptime(time_start, "%Y-%m-%d %H:%M")
                time_end = datetime.strptime(time_end, "%Y-%m-%d %H:%M")
            elif len(time_start) == 10:
                time_start = datetime.strptime(time_start + ' 00:00', "%Y-%m-%d %H:%M")
                time_end = datetime.strptime(time_end + ' 23:59', "%Y-%m-%d %H:%M")

        if not (isinstance(time_start, datetime) or isinstance(time_end, datetime)):
            raise ValueError(f"类型错误：{type(time_start) = } {type(time_end) = }")

        _o = "" if not kwargs else " AND " + " AND ".join(f"{k} LIKE '%{v}%' " for k, v in kwargs.items())
        if not force_imap:
            _ts = time_start.strftime("%Y-%m-%d %H:%M")
            _te = time_end.strftime("%Y-%m-%d %H:%M")
            cur = self.db.execute(
                f"SELECT uid, mail_id, subject, send_time, sender, body, attachments FROM `mails` "
                f"WHERE subject LIKE '%{subject}%' "
                f" AND send_time >= '{_ts}' "
                f" AND send_time <= '{_te}' "
                f" {_o} "
                f" ORDER BY send_time DESC",
            )
            rows = cur.fetchall()
            if rows:
                logger.info(f"命中缓存： ")
                return Mail(**rows[0])

        return self.search_email_from_imap(subject, time_start, time_end, folder)

    def search_email_from_imap(
            self, subject, time_start: datetime, time_end: datetime, folder
    ) -> Mail:
        """从IMAP中查询邮件

        :param subject:
        :param time_start:
        :param time_end:
        :param folder:
        :return:
        """
        if self.imap is None:
            raise ConnectionError(
                f"IMAP 未初始化. 查询失败 {subject=}, {time_start.strftime('%Y-%m-%d %H:%M')} -- {time_end.strftime('%Y-%m-%d %H:%M')}"
            )
        _st, count = imap.select(folder, readonly=True)
        if _st != 'OK':
            logger.warning(f"IMAP: SELECT ERROR. {_st} {count}, ({folder=})")
            raise
        logger.info(f"SELECT {folder}, Mail: {count[0]}")
        all_uids = []
        print_end = time_end.strftime("%Y-%m-%d %H:%M")
        while time_start.date() <= time_end.date():
            search_str = f'(ON "{time_end.strftime("%d-%b-%Y")}" SUBJECT "{subject}")'
            logger.debug(f"IMAP: SEARCH: {search_str}")
            _st, uids = self.imap.uid('SEARCH', None, search_str)
            time_end: datetime = time_end - timedelta(days=1)
            for uid in uids:
                all_uids.extend(_ for _ in uid.decode().split(' ') if _ != '')

        logger.info(f"IMAP: SEARCH FIND: {all_uids}")
        if not all_uids:
            logger.error(f"IMAP:没查到邮件 {subject} [{time_start} to {time_end}]")
            raise FileNotFoundError(f"IMAP:没查到邮件 {subject} at [{time_start} to {print_end}] in {folder}")

        b_start = 0
        mail = Mail.default()
        while b_start < len(all_uids):
            end = min(b_start + 10, len(all_uids))
            typ, msg_data = self.imap.uid(
                'FETCH', ','.join(all_uids[b_start:end]),
                # '(RFC822)'
                # '(BODYSTRUCTURE)' BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT FROM)] INTERNALDATE
                '(INTERNALDATE RFC822)'
            )
            b_start = end
            if typ != 'OK':
                logger.warning(f"FETCH Error: {typ} {msg_data} (uids={all_uids[b_start:end]})")
                continue

            # print(msg_data, )
            for _ in range(0, len(msg_data), 2):  # TODO 兼容性
                # recv_time = re.findall(
                #     r'INTERNALDATE "(\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2} [+-]\d{4})"', msg_data[_][0].decode())[0]
                uid = re.findall(r'UID (\d+)', msg_data[_ + 1].decode())[0]
                rfc822 = msg_data[_][1]
                logger.debug(f'IMAP： 获取到邮件： {uid = } {rfc822[:70]=}')

                mail = self.parse_rfc822(rfc822)
                mail.uid = uid
                self.insert_mail(**mail.to_dict())
        if not mail.subject:
            logger.error(f"IMAP: 没有获取到邮件: {mail.subject}")
            raise FileNotFoundError(f"IMAP: 没有获取到邮件: {mail.subject}")
        return mail

    @staticmethod
    def _decode_str(s):
        """解码邮件标题/内容，解决乱码问题"""
        value, charset = decode_header(s)[0]
        if charset:
            value = value.decode(charset, errors="ignore")
        return value

    @staticmethod
    def _decode_header_value(raw_val: Optional[str]) -> str:
        """解码RFC2047编码头（主题、名称等）"""
        if not raw_val:
            return ""
        buf = ""
        for data, charset in decode_header(raw_val):
            if isinstance(data, bytes):
                buf += data.decode(charset or "utf-8", errors="replace")
            else:
                buf += data
        return buf

    def _split_address_list(self, raw_addr: Optional[str]) -> list[str]:
        """分割 To/Cc 多地址，格式化：姓名 <email@xx.com>"""
        result = []
        if not raw_addr:
            return result
        # 简单分割，兼容逗号分隔的收件人
        for addr_part in raw_addr.split(","):
            addr_part = addr_part.strip()
            if not addr_part:
                continue
            display_name, email_addr = parseaddr(addr_part)
            display_name = self._decode_header_value(display_name)
            if display_name:
                result.append(f'"{display_name}" <{email_addr}>')
            else:
                result.append(email_addr)
        return result

    def parse_rfc822(self, raw_email: bytes) -> Mail:
        """解析RFC822邮件

        :param raw_email: RFC822格式邮件原文, bytes
        :return: {
            subject:
            send_time:
            sender:
            "recipient":
            "cc":
            body: {
                text: "", (如果有)
                html: "",(如果有)
            }
            attachments: {
                name: data (如果有)
            }
        }
        """
        logger.debug(f"parse_rfc822: {raw_email}")
        msg = email.message_from_bytes(raw_email)

        email_id = self._decode_header_value(msg.get("Message-ID", ""))

        # 1. 主题
        subject = self._decode_header_value(msg.get("Subject", ""))

        # 2. 发件人
        from_raw = self._decode_header_value(msg.get("From", ""))
        disp_name, sender_addr = parseaddr(from_raw)
        disp_name = self._decode_header_value(disp_name)
        if disp_name:
            sender = f'"{disp_name}" <{sender_addr}>'
        else:
            sender = sender_addr

        # 3. 收件人、抄送
        # to_header = msg.get("To", "")
        # cc_header = msg.get("Cc", "")
        # recipient = self._split_address_list(to_header)
        # cc = self._split_address_list(cc_header)

        # 4. 邮件发送时间（邮件头Date，发件客户端时间；不是INTERNALDATE）
        send_time = None
        date_raw = msg.get("Date")
        if date_raw:
            try:
                send_time = parsedate_to_datetime(date_raw)
            except Exception:
                send_time = None

        # 5. 正文 text/plain + text/html
        body_text = ""
        body_html = ""

        # 6. 附件 {文件名: bytes数据}
        attachments: Dict[str, bytes] = {}

        for part in msg.walk():
            # 跳过容器multipart
            if part.is_multipart():
                continue

            ctype = part.get_content_type().lower()
            filename = part.get_filename()

            payload = part.get_payload(decode=True)
            if payload is None:
                continue

            # 判断附件：存在文件名 → 附件
            if filename:
                file_name_decoded = self._decode_header_value(filename)
                attachments[file_name_decoded] = payload
                continue

            # 纯文本正文
            charset = part.get_charset()
            enc = charset if charset else "utf-8"
            try:
                text_data = payload.decode(enc, errors="replace")
            except Exception:
                text_data = payload.decode("utf-8", errors="replace")

            if ctype == "text/plain":
                body_text = text_data
            elif ctype == "text/html":
                body_html = text_data

        return Mail(
            # uid, mail_id, subject, send_time, sender, body, attachments
            uid=None,
            mail_id=email_id,
            subject=subject,
            send_time=send_time,
            sender=sender,
            body={
                "text": body_text,
                "html": body_html
            },
            attachments=attachments,
        )
        # {
        #     "mail_id": email_id,
        #     "subject": subject,
        #     "send_time": send_time,
        #     "sender": sender,
        #     "recipient": recipient,
        #     "cc": cc,
        #     "body": {
        #         "text": body_text,
        #         "html": body_html
        #     },
        #     "attachments": attachments
        # }


if __name__ == '__main__':
    logging.basicConfig(level='DEBUG', format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    imap = get_imap(
        'imap.feishu.cn',
        993,
        'lcq@leecq.cn',
        'Ftkt8ynJ1sfYB0ME',
        ssl=True,
    )
    em = MailManager(imap)
    em.search_email("", '2026-07-21', '2026-07-31', folder="INBOX")
