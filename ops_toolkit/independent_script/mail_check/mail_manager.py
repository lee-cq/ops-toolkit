#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : mail_manager
@Author     : LeeCQ
@Date-Time  : 2026/7/30


TODO
1.

"""

import logging
import imaplib
import re
import sqlite3
import email
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
import base64
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Dict, Iterator, Optional, Iterable

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Union

logger = logging.getLogger("mail_check.mail_manager")

# IMAP SEARCH 协议要求英文月份缩写，避免依赖系统 locale（如 zh_CN 下 %b 输出“8月”导致查询失败）
_IMAP_MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

# mails 表中允许被 SQL 参数化查询的字段白名单，防止注入
_MAIL_COLUMNS = {
    "uid",
    "mail_id",
    "folder",
    "subject",
    "sender",
    "recipients",
    "cc",
    "body",
}


def _imap_date_str(dt: datetime) -> str:
    """datetime → IMAP日期格式 DD-Mon-YYYY（固定英文月份，不受系统 locale 影响）"""
    return f"{dt.day:02d}-{_IMAP_MONTHS[dt.month - 1]}-{dt.year}"


def _to_local_naive(dt: datetime | None) -> datetime | None:
    """带时区的 datetime 统一转为本地 naive 时间，保证与 SQLite 字符串比较语义一致"""
    if dt is None or isinstance(dt, str):
        return dt
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def get_imap(host, port, user, password, ssl=True) -> imaplib.IMAP4_SSL | imaplib.IMAP4:
    _imap = None
    try:
        if ssl:
            _imap = imaplib.IMAP4_SSL(host, port)
        else:
            _imap = imaplib.IMAP4(host, port)

        _status, data = _imap.login(user, password)
        if _status == "OK":
            logger.info(f"IMAP: {host}:{port} [{ssl=}] {user} 登录成功 .")
            return _imap
        logger.error(f"IMAP: {host}:{port} [{ssl=}] {user} 登录失败 .")
        raise ValueError(f"IMAP: {host}:{port} [{ssl=}] {user} 登录失败: {data}")
    except Exception:
        # 连接/登录失败时释放连接；直接 re-raise 保留原始 traceback
        if _imap is not None:
            try:
                _imap.logout()
            except Exception:
                pass
        raise


def get_imap_from_env():
    try:
        _port = int(os.environ.get("IMAP_PORT", 143))
    except (TypeError, ValueError):
        logger.warning(
            f"IMAP_PORT 环境变量非法: {os.environ.get('IMAP_PORT')!r}，使用默认值 143"
        )
        _port = 143
    return get_imap(
        os.environ.get("IMAP_HOST"),
        _port,
        os.getenv("IMAP_USERNAME"),
        os.getenv("IMAP_PASSWORD"),
        ssl=os.getenv("IMAP_SSL", "").upper() in ["TRUE", "1", "T"],
    )


@dataclass
class Mail:
    # uid, mail_id, subject, send_time, sender, body, attachments, folder
    uid: str
    mail_id: str
    subject: str
    send_time: datetime | None
    sender: str
    recipients: str  # , 分隔的收件人列表
    cc: str  # , 分隔的抄送列表
    body: dict | str | None
    attachments: Dict[str, str | bytes] | None
    folder: str = "INBOX"
    _manager: "MailManager" = None

    def _ensure_full(self):
        """确保正文/附件已加载；缺失时从服务器重新拉取并回填到当前对象"""
        if self.attachments is not None and self.body is not None:
            return
        if self._manager is None:
            raise ConnectionError("Mail 未绑定 MailManager，无法从服务器拉取内容")
        if not self.folder:
            raise ValueError("Mail 未指定 Folder，无法获取内容")
        fresh = next(
            self._manager.get_mail_by_uid(self.uid, folder=self.folder, with_body=True),
            None,
        )
        if fresh is None:
            raise LookupError(f"服务器上未找到 UID={self.uid} 的邮件")
        # 直接回填当前对象字段，保证调用方持有的对象生效（局部重赋值 self 无效）
        self.body = fresh.body
        self.attachments = fresh.attachments

    def list_attachments(self):
        self._ensure_full()
        if isinstance(self.attachments, str):
            self.attachments = json.loads(self.attachments)
        return tuple(self.attachments.keys())

    def get_attachment(self, name=None) -> bytes:
        self._ensure_full()
        if isinstance(self.attachments, str):
            self.attachments = json.loads(self.attachments)
        if not self.attachments:
            raise FileNotFoundError(f"UID={self.uid} 的邮件没有附件")
        if name is None:
            name = next(iter(self.attachments))
        data = self.attachments[name]
        # 内存态附件是原始 bytes，直接返回；数据库缓存态是 base64 字符串，需解码
        if isinstance(data, str):
            return base64.b64decode(data)
        return data

    def get_body(self) -> dict:
        self._ensure_full()
        if isinstance(self.body, str):
            self.body: dict = json.loads(self.body)
            return self.body
        elif isinstance(self.body, dict):
            return self.body
        raise ValueError(f"Type Error: {type(self.body).__name__} Error")

    def get_text(self) -> str:
        return self.get_body().get("text") or ""

    def get_html(self) -> str:
        _bd = self.get_body()
        return _bd.get("html") or _bd.get("text") or ""

    def get_send_time(self) -> datetime:
        if isinstance(self.send_time, str):
            return datetime.strptime(self.send_time.split("+")[0], "%Y-%m-%d %H:%M:%S")
        if isinstance(self.send_time, datetime):
            return self.send_time
        raise ValueError(f"{self.send_time=} Error")

    @classmethod
    def default(cls):
        return cls(
            uid="",
            mail_id="",
            subject="",
            send_time=datetime.now(),
            sender="",
            recipients="",
            cc="",
            body={},
            attachments={},
        )

    def to_dict(self):
        return {
            "uid": self.uid,
            "mail_id": self.mail_id,
            "folder": self.folder,
            "subject": self.subject,
            "send_time": self.send_time,
            "sender": self.sender,
            "recipients": self.recipients,
            "cc": self.cc,
            "body": self.body,
            "attachments": self.attachments,
        }


class ImapFolder:
    """
    IMAP 文件夹封装类
    raw: IMAP LIST 返回的原始行(bytes)，例 b'(\\HasNoChildren) "/" "INBOX"'

    >>> ImapFolder(b'(\\\\Noinferiors) "/" INBOX').display_name
    """

    # IMAP LIST 响应正则 RFC3501
    _RE_LIST_LINE = re.compile(
        r"\((?P<flags>.*?)\)\s+"  # flags (...)
        r'"(?P<delim>.*?)"\s+'  # 分隔符永远带引号
        r'(?:"(?P<name_quoted>.*)"|(?P<name_atom>\S+))'  # 名字：引号包裹 或者 atom无引号
    )

    def __init__(self, raw: str | bytes):
        self.raw: str | bytes = raw
        self._flags: list[str] = []
        self._delimiter: str = ""
        self._imap_raw_name: str = ""
        self._size: Optional[int] = None

        if isinstance(raw, bytes):
            text = raw.decode("ascii")
        else:
            text = raw

        m = self._RE_LIST_LINE.match(text)
        if not m:
            raise ValueError(f"解析IMAP LIST行失败: {text}")

        gd = m.groupdict()
        self._flags = gd["flags"].split() if gd["flags"] else []
        self._delimiter = gd["delim"]
        # 优先取引号内，没有就取atom
        self._imap_raw_name = (
            gd["name_quoted"] if gd["name_quoted"] is not None else gd["name_atom"]
        )

    @classmethod
    def modified_utf7_decode(cls, s: str) -> str:
        """IMAP Modified‑UTF7 解码 -> 用于展示"""
        out = []
        i = 0
        length = len(s)
        while i < length:
            c = s[i]
            if c == "&":
                end = s.find("-", i)
                if end == -1:
                    out.append(s[i:])
                    break
                b64 = s[i + 1 : end].replace(",", "/")
                pad = (-len(b64)) % 4
                b64 += "=" * pad
                bin_data = base64.b64decode(b64)
                out.append(bin_data.decode("utf-16-be"))
                i = end + 1
            else:
                out.append(c)
                i += 1
        return "".join(out)

    @classmethod
    def modified_utf7_encode(cls, s: str) -> str:
        """IMAP Modified‑UTF7 编码 -> 协议调用select使用"""
        out = []
        for ch in s:
            cp = ord(ch)
            if 0x20 <= cp <= 0x7E and ch != "&":
                out.append(ch)
            else:
                out.append("&")
                b = ch.encode("utf-16-be")
                b64 = base64.b64encode(b).decode("ascii").rstrip("=").replace("/", ",")
                out.append(b64)
                out.append("-")
        return "".join(out)

    @property
    def tag(self) -> list[str]:
        """文件夹标记，如 ['\\Noinferiors','\\Trash']"""
        return self._flags

    @property
    def name(self) -> str:
        """IMAP协议原始文件夹名，select()必须传这个"""
        return self._imap_raw_name

    @property
    def display_name(self) -> str:
        """可读显示名称，中文已解码"""
        return self.modified_utf7_decode(self._imap_raw_name)

    @property
    def size(self) -> Optional[int]:
        """
        文件夹邮件总数，LIST命令不返回；
        需要调用 fill_size(imap_conn) 执行select后填充
        """
        return self._size

    def fill_size(self, imap_conn):
        """
        执行SELECT获取文件夹邮件总数，填充self._size
        :param imap_conn: imaplib.IMAP4_SSL 实例
        """
        status, data = imap_conn.select(self.name, readonly=True)
        if status != "OK":
            raise RuntimeError(f"select folder failed: {status}")
        if data and data[0] is not None:
            self._size = int(data[0])
        else:
            self._size = 0

    def __repr__(self):
        return f"<ImapFolder display={self.display_name!r} size={self.size}>"


class MailManager:

    def __init__(
        self,
        imap: imaplib.IMAP4 | imaplib.IMAP4_SSL = None,
        cache_db=None,
    ):
        self.sqlite_adapter()
        self.db_path = cache_db or "./cache_mail_manager.db"
        self.db = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.db.row_factory = sqlite3.Row
        self.init_db()
        self.imap = imap or (
            get_imap_from_env() if os.environ.get("IMAP_HOST") else None
        )
        logger.info(f"MailManager inited, cache_db = {self.db_path.__str__()}")

    @staticmethod
    def sqlite_adapter():
        """"""
        sqlite3.register_adapter(dict, lambda d: json.dumps(d, ensure_ascii=False))
        sqlite3.register_converter("JSON", json.loads)

        sqlite3.register_adapter(datetime, lambda d: d.strftime("%Y-%m-%d %H:%M:%S"))
        sqlite3.register_converter(
            "DATETIME",
            lambda d: datetime.strptime(d.decode()[:19], "%Y-%m-%d %H:%M:%S"),
        )

    def close(self):
        """释放 IMAP 与 SQLite 连接"""
        if self.imap is not None:
            try:
                self.imap.logout()
            except Exception:
                pass
            self.imap = None
        if self.db is not None:
            try:
                self.db.close()
            except Exception:
                pass
            self.db = None

    @staticmethod
    def verify_query_time(
        time_start: datetime | str, time_end: datetime | str
    ) -> tuple[datetime, datetime]:
        """"""
        if isinstance(time_start, str) and isinstance(time_end, str):
            if len(time_start) != len(time_end) or len(time_start) not in (5, 10, 16):
                raise ValueError(
                    "time_start 和 time_end 长度必须相同, 且长度必须是 5(01:01) / 10(2026-01-01) / 16(2026-01-01 01:01)"
                )
            if len(time_start) > 9 and time_end < time_start:
                raise ValueError("指定日期时，time_end必须大于time_start")
            if len(time_start) == 5:
                today = datetime.today().strftime("%Y-%m-%d ")
                time_start = datetime.strptime(today + time_start, "%Y-%m-%d %H:%M")
                time_end = datetime.strptime(today + time_end, "%Y-%m-%d %H:%M")
                if time_start > time_end:
                    time_start = time_start - timedelta(days=1)
                return time_start, time_end
            elif len(time_start) == 16:
                time_start = datetime.strptime(time_start, "%Y-%m-%d %H:%M")
                time_end = datetime.strptime(time_end, "%Y-%m-%d %H:%M")
                return time_start, time_end
            elif len(time_start) == 10:
                time_start = datetime.strptime(time_start + " 00:00", "%Y-%m-%d %H:%M")
                time_end = datetime.strptime(time_end + " 23:59", "%Y-%m-%d %H:%M")
                return time_start, time_end

        elif isinstance(time_start, datetime) and isinstance(time_end, datetime):
            return time_start, time_end

        # if not (isinstance(time_start, datetime) or isinstance(time_end, datetime)):
        raise ValueError(f"类型错误：{type(time_start) = } {type(time_end) = }")

    def init_db(self):
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS mails ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " uid TEXT NOT NULL UNIQUE,"
            " mail_id Text unique,"
            " folder TEXT ,"
            " subject Text not null,"
            " send_time DateTime,"
            " sender text not null,"
            " recipients text, "
            " cc text ,"
            " body JSON, "
            " attachments JSON "
            " )",
        )
        self.db.commit()

    # noinspection PyTypeChecker
    def insert_mail(self, mails: Mail | Iterable[Mail]):
        """缓存邮件"""
        if isinstance(mails, Mail):
            mails = [mails]

        for mail in mails:
            # 无 Message-ID 时用 UID 兜底，避免多封无 ID 邮件 mail_id="" 互相覆盖
            if not mail.mail_id:
                mail.mail_id = f"NO-MESSAGE-ID:{mail.uid or ''}"
            if mail.attachments:
                mail.attachments = {
                    k: base64.encodebytes(_v).decode("ascii")
                    for k, _v in mail.attachments.items()
                }
        _rows = [
            (
                mail.uid,
                mail.mail_id,
                mail.folder,
                mail.subject,
                mail.send_time,
                mail.sender,
                mail.recipients,
                mail.cc,
                mail.body,
                json.dumps(mail.attachments),
            )
            for mail in mails
        ]

        _sql = (
            "INSERT INTO `mails` "
            "(uid, mail_id, folder, subject, send_time, sender, recipients, cc, body, attachments) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(mail_id) DO UPDATE SET "
            "body=excluded.body, attachments=excluded.attachments"
        )
        try:
            self.db.executemany(_sql, _rows)
            self.db.commit()
        except Exception as _e:
            # 单条失败不影响其它邮件入库
            logger.warning(
                f"批量缓存邮件失败，降级为逐条缓存(uids={[_.uid for _ in mails]}): {_e}"
            )
            for _r in _rows:
                try:
                    self.db.execute(_sql, _r)
                except Exception as _e:
                    logger.error(f"缓存邮件失败(uid={_r[0]}) subject={_r[3]}, : {_e}")
        logger.debug(f"缓存已提交 「{[mail.uid for mail in mails]}」")

    def cached_uids(self, need_body=False) -> set:
        _w = "where body is not NULL" if need_body else ""
        return set(
            i["uid"]
            for i in self.db.execute(f"SELECT uid FROM `mails` {_w}").fetchall()
        )

    def create_sql_where(
        self,
        subject,
        time_start: datetime | str,
        time_end: datetime | str,
        where_sql: str = "",
        **kwargs,
    ) -> str:
        time_start, time_end = self.verify_query_time(time_start, time_end)

        # 字段白名单校验，防止拼接非法列名
        for _k in kwargs:
            if _k not in _MAIL_COLUMNS:
                raise ValueError(
                    f"非法查询字段: {_k!r}，允许的字段: {sorted(_MAIL_COLUMNS)}"
                )

        # 参数化查询，杜绝 SQL 注入
        _o = ""
        _kw_params: list = []
        for _k, _v in kwargs.items():
            _o += f" AND `{_k}` LIKE ? "
            _kw_params.append(f"%{_v}%")

        # 秒级字符串比较；上界取开区间（< end+1s），保证结束时刻最后一分钟的邮件不被漏掉
        _ts = time_start.strftime("%Y-%m-%d %H:%M:%S")
        _te = time_end.strftime("%Y-%m-%d %H:%M:%S")
        _params = [f"%{subject}%", _ts, _te, *_kw_params]

        return (
            f"WHERE subject LIKE ? "
            f" AND send_time >= ? "
            f" AND send_time < ? "
            f" {_o} {where_sql}"
        ), _params

    def search_email_newest(
        self,
        subject,
        time_start: datetime | str,
        time_end: datetime | str,
        /,
        folder="inbox",
        **kwargs,
    ) -> Mail | None:
        """在给定条件约束下内找到最新的一封邮件，

        :param subject:
        :param time_start:
        :param time_end:
        :param folder:
        :param kwargs:
        :return: Mail
        """
        _ms = {
            (
                m.send_time.strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(m.send_time, datetime)
                else str(m.send_time)
            ): m
            for m in self.search_email(subject, time_start, time_end, folder, **kwargs)
        }
        if not _ms:
            return None
        return _ms[max(list(_ms.keys()))]

    def search_email(
        self,
        subject,
        time_start: datetime | str,
        time_end: datetime | str,
        /,
        folder="inbox",
        where_sql: str = "",
        is_desc: bool = True,
        _recached=False,
        _fetchd_body=False,
        **kwargs,
    ) -> Iterator[Mail]:
        """从缓存数据库中查询邮件，如果没找到去imap中找

        :param subject: 邮件标题
        :param time_start: 搜索的起始时间
        :param time_end: 搜索的结束时间
        :param folder: 检索的目录 - 仅缓存邮件使用，默认在数据库中全局搜索
        :param is_desc: 是否倒序
        :param where_sql: WEERE 查询的SQL原文，将原样拼接到查询后面，以OR AND 开头
        :param _recached:

        :return: Iterator[Mail] 返回Mail对象的生成器
        """
        if "body" in kwargs.keys():
            logger.info("查询条件中包含BODY, 检查并缓存BODY.")
            _ws, _wa = self.create_sql_where(
                subject,
                time_start,
                time_end,
                where_sql,
                **{k: v for k, v in kwargs if k != "body"},
            )
            _sql = (
                "SELECT folder, GROUP_CONCAT(DISTINCT uid) AS uids from `mails` "
                f"WHERE {_ws} and body is NULL "
                "GROUP BY folder",
            )
            no_body = self.db.execute(_sql, _wa).fetchall()
            for f, uids in no_body:
                logger.debug(f"CACHE BODY: {f}: {uids}")
                self.get_mail_by_uid(uids, with_body=True, folder=f)

        _d = "desc" if is_desc else "asc"
        _ws, _wa = self.create_sql_where(
            subject, time_start, time_end, where_sql, **kwargs
        )
        _sql = (
            f"SELECT uid, mail_id, folder, subject, send_time, sender, recipients, cc, body, attachments FROM `mails` WHERE {_ws} "
            f" ORDER BY send_time {_d}"
        )
        rows = self.db.execute(_sql, _wa).fetchall()
        # rows = cur.fetchall()
        if rows:
            for _m in rows:
                yield Mail(**_m, _manager=self)
        else:
            if not _recached:
                logger.debug("Recache")
                _c_b = True if "body" in kwargs.keys() else False
                self.cache_message_info(time_start, time_end, folder, with_body=_c_b)
                yield from self.search_email(
                    subject,
                    time_start,
                    time_end,
                    folder=folder,
                    _recached=True,
                    **kwargs,
                )
            else:
                # 缓存与 IMAP 均无匹配是正常场景，正常结束迭代
                return

    def list_folder(self, directory='""', pattern="*") -> Iterator[ImapFolder]:
        """列出邮箱中的所有folder"""
        if self.imap is None:
            raise ConnectionError(f"IMAP 未初始化. ")

        _st, data = self.imap.list(directory, pattern)
        if _st != "OK":
            logger.error(f"列出目录失败，{_st}, {data}")
            return
        for raw in data:
            logger.debug(f"IMAP: FOLDER: ROW DATA: {raw}")
            yield ImapFolder(raw)

    def cache_message_info(
        self,
        time_start: datetime | str,
        time_end: datetime | str,
        folder="INBOX",
        with_body=False,
    ) -> None:
        """从服务缓存邮件

        :param time_start:
        :param time_end:
        :param folder:
        :param with_body:
        :return:
        """
        time_start, time_end = self.verify_query_time(time_start, time_end)
        if self.imap is None:
            raise ConnectionError(f"IMAP 未初始化. ")

        if folder == "ALL":
            logger.info("遍历全部Folder查找邮件 ...")
            for _f in self.list_folder():
                self.cache_message_info(time_start, time_end, _f.name, with_body)
            return

        _st, count = self.imap.select(folder, readonly=True)
        if _st != "OK":
            raise NotADirectoryError(f"IMAP: SELECT ERROR. {_st} {count}, ({folder=})")

        logger.info(f"SELECT {folder}, Mail: {count[0]}")
        # BEFORE 为排他条件，故结束时间 +1 天；月份用固定英文缩写，不受系统 locale 影响
        search_str = (
            f'(SINCE "{_imap_date_str(time_start)}" '
            f'BEFORE "{_imap_date_str(time_end + timedelta(days=1))}")'
        )  # SUBJECT "{subject}"
        logger.debug(
            f"IMAP: SEARCH: {search_str}, folder={ImapFolder.modified_utf7_decode(folder)}"
        )
        _st, uids = self.imap.uid("SEARCH", None, search_str)
        all_uids = (
            [_ for uid in uids for _ in uid.decode().split() if _ != ""]
            if _st == "OK"
            else []
        )

        logger.info(f"IMAP: SEARCH FIND: {all_uids}")
        if not all_uids:
            logger.warning(f"IMAP:没查到邮件 {search_str}")
            return
        _cached = self.cached_uids(with_body)
        all_uids = list(set(all_uids) - _cached)  #
        logger.info(f"已缓存的ID: [{_cached & set(all_uids)}]")
        logger.info(f"从服务器拉取: [{all_uids}]")

        for uids in [all_uids[i : i + 30] for i in range(0, len(all_uids), 30)]:
            list(self.get_mail_by_uid(uids, with_body=with_body, folder=folder))

    def get_mail_by_uid(
        self, uids: str | Iterable[str], with_body=False, folder="INBOX"
    ) -> Iterator[Mail]:
        """

        :param uids:
        :param with_body:
        :param folder:
        :return:
        """
        if self.imap is None:
            raise ConnectionError(f"IMAP 未初始化. ")

        _st, count = self.imap.select(folder, readonly=True)
        if _st != "OK":
            raise NotADirectoryError(f"IMAP: SELECT ERROR. {_st} {count}, ({folder=})")

        if isinstance(uids, str):
            uids = uids.split(",")
        uids = sorted(list(set(uids)))
        logger.info(f"IMAP: FETCH: {uids} ({with_body=})")
        uids = ",".join(uids)

        typ, msg_data = self.imap.uid(
            "FETCH",
            uids,
            (
                "(BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT DATE FROM TO CC)])"
                if not with_body
                else "BODY[]"
            ),
        )
        if typ != "OK":
            logger.warning(f"FETCH Error: {typ} {msg_data} (uids={uids})")
            return

        mails = []
        try:
            for _ in range(0, len(msg_data), 2):  # TODO 兼容性
                # recv_time = re.findall(
                #     r' INTERNALDATE "(\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2} [+-]\d{4})"', msg_data[_][0].decode())[0]
                uid = re.findall(r"UID (\d+)", msg_data[_ + 1].decode())[0]
                rfc822 = msg_data[_][1]
                logger.debug(f"IMAP： 获取到邮件： {uid = }")

                mail = self.parse_rfc822(rfc822)
                mail.uid = uid
                mail.folder = folder
                if not with_body:
                    mail.attachments = None
                    mail.body = None
                mails.append(mail)
                yield mail
        except Exception as e:
            logger.error(f"IMAP: FETCH ERROR: {e}")
        finally:
            logger.info(f"缓存邮件, {len(mails)} mails")
            self.insert_mail(mails)

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

    def get_inter_time(self, uid) -> datetime|None:
        if self.imap is None:
            logger.error(
                f"IMAP 未初始化"
            )
            return None
        else:
            status, data = self.imap.uid("FETCH", uid, "INTERNALDATE")
            if status != "OK":
                logger.error(f"获取邮件时间失败：{uid}")
                return None
            else:
                try:
                    resp = data[0].decode()
                    send_time = _to_local_naive(
                        parsedate_to_datetime(
                            resp.split('INTERNALDATE "')[1].split('"')[0]
                        )
                    )
                    return send_time
                except Exception as _e:
                    logger.error(
                        f"INTERNALDATE 解析失败, {_e}： {uid}"
                    )
        

    def parse_rfc822(self, raw_email: bytes) -> Mail:
        """解析RFC822邮件

        :param raw_email: RFC822格式邮件原文, bytes
        :return: Mail({
            subject:
            send_time:
            sender:
            "recipients":
            "cc":
            body: {
                text: "", (如果有)
                html: "",(如果有)
            }
            attachments: {
                name: data (如果有)
            }
        })
        """
        msg = email.message_from_bytes(raw_email)
        email_id = self._decode_header_value(msg.get("Message-ID", ""))

        # 1. 主题
        subject = (
            self._decode_header_value(msg.get("Subject", ""))
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
        )

        # 2. 发件人
        from_raw = self._decode_header_value(msg.get("From", ""))
        disp_name, sender_addr = parseaddr(from_raw)
        disp_name = self._decode_header_value(disp_name)
        if disp_name:
            sender = f'"{disp_name}" <{sender_addr}>'
        else:
            sender = sender_addr

        # 3. 收件人、抄送
        recipients = self._split_address_list(msg.get("To", ""))
        cc = self._split_address_list(msg.get("Cc", ""))

        # 4. 邮件发送时间（邮件头Date，发件客户端时间；不是INTERNALDATE）
        date_raw = msg.get("Date", "").split(" +")[0]
        send_time = _to_local_naive(parsedate_to_datetime(date_raw))

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
            payload = payload if isinstance(payload, bytes) else b""
            # 判断附件：存在文件名 → 附件
            if filename:
                file_name_decoded = self._decode_header_value(filename)
                attachments[file_name_decoded] = payload
                continue

            # 纯文本正文
            enc = part.get_charset() or "utf-8"
            try:
                text_data = payload.decode(enc, errors="replace")
            except Exception:
                text_data = payload.decode("utf-8", errors="replace")

            if ctype == "text/plain":
                body_text = text_data
            elif ctype == "text/html":
                body_html = text_data

        return Mail(
            # uid, mail_id, subject, send_time, sender, recipients, cc, body, attachments
            uid="",
            mail_id=email_id,
            subject=subject,
            send_time=send_time,
            sender=sender,
            recipients=", ".join(recipients),
            cc=", ".join(cc),
            body={"text": body_text, "html": body_html},
            attachments=attachments,
        )


def get_smtp(host, port, user, password, ssl=True) -> smtplib.SMTP | smtplib.SMTP_SSL:
    _smtp = None
    data = None
    if not host or not user:
        raise ConnectionError("没有指定Host or User")
    try:
        if ssl:
            _smtp = smtplib.SMTP_SSL(host, port)
        else:
            _smtp = smtplib.SMTP(host, port)

        data = _smtp.login(user, password)
        logger.info(f"SMTP: {host}:{port} [{ssl=}] {user} 登录成功 .")
        return _smtp

    except smtplib.SMTPAuthenticationError as _e:
        logger.error(f"IMAP: {host}:{port} [{ssl=}] {user} 登录失败: {data}")
        raise _e
    except Exception:
        # 连接/登录失败时释放连接；直接 re-raise 保留原始 traceback
        logger.error(f"IMAP: {host}:{port} [{ssl=}] {user} 连接失败: {data}")
        raise


def get_smtp_from_env():
    use_ssl = os.getenv("SMTP_SSL", "").upper() in ["TRUE", "1", "T"]
    try:
        _port = int(
            os.environ.get(
                "SMTP_PORT", smtplib.SMTP_SSL_PORT if use_ssl else smtplib.SMTP_PORT
            )
        )
    except (TypeError, ValueError):
        logger.warning(
            f"SMTP_PORT 环境变量非法: {os.environ.get('SMTP_PORT')!r}，使用默认值 25 / 465"
        )
        _port = smtplib.SMTP_SSL_PORT if use_ssl else smtplib.SMTP_PORT
    return get_smtp(
        os.environ.get("SMTP_HOST"),
        _port,
        os.getenv("SMTP_USERNAME"),
        os.getenv("SMTP_PASSWORD"),
        ssl=os.getenv("SMTP_SSL", "").upper() in ["TRUE", "1", "T"],
    )


def send_email(
    smtp: smtplib.SMTP | smtplib.SMTP_SSL | None,
    subject: str,
    body: str,
    to: Union[str, List[str]],
    _from: str = None,
    atta: Optional[List[str | Path]] | Path = None,
    cc: Optional[Union[str, List[str]]] = None,
    bcc: Optional[Union[str, List[str]]] = None,
) -> bool:
    """通过已建立连接的SMTP会话发送邮件，返回发送状态
    自动识别正文：包含 <html> / <body> 标签则作为HTML邮件，否则为纯文本邮件

    :param smtp: 已经 login 完成的 smtplib.SMTP/SMTP_SSL 对象
    :param subject: 邮件主题
    :param body: 邮件正文，可以是纯文本或者HTML源码
    :param atta: 附件文件路径列表,无附件传None或空列表
    :param _from: 发件人地址
    :param to: 收件人，单个地址字符串 / 地址列表
    :param cc: 抄送，单个地址字符串 / 地址列表，可选
    :param bcc: 密送，单个地址字符串 / 地址列表，可选
    :return: 成功返回True，发生异常返回False
    """
    smtp = smtp or get_smtp_from_env()
    if not smtp:
        logger.error("smtp对象不能为空，请先完成smtp连接与登录")
        return False

    # 统一转为列表
    def norm_addr(addr: Optional[Union[str, List[str]]]) -> List[str]:
        if not addr:
            return []
        if isinstance(addr, str):
            return [a.strip() for a in addr.split(",") if a.strip()]
        return list(addr)

    to_list = norm_addr(to)
    cc_list = norm_addr(cc)
    bcc_list = norm_addr(bcc)
    all_recipients = to_list + cc_list + bcc_list

    if not all_recipients:
        raise ValueError("收件人、抄送、密送不能全部为空")

    if not _from:
        _from = smtp.user

    msg = MIMEMultipart()
    msg["From"] = _from
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject

    # 自动判断是否HTML正文
    body_lower = body.lower()
    if "</html>" in body_lower or "</body>" in body_lower:
        mime_subtype = "html"
    else:
        mime_subtype = "plain"

    msg.attach(MIMEText(body, mime_subtype, "utf-8"))

    # 添加附件
    if atta:
        if not isinstance(atta, Iterable):
            atta = [atta]
        for file_path in atta:
            try:
                file_path = Path(file_path)
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file_path.read_bytes())
                encoders.encode_base64(part)
                filename = file_path.name
                part.add_header(
                    "Content-Disposition", f'attachment; filename="{filename}"'
                )
                msg.attach(part)
            except OSError:
                continue

    try:
        smtp.sendmail(_from, all_recipients, msg.as_string())
        return True
    except smtplib.SMTPException:
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level="DEBUG", format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
    )
    imaplib.Debug = 3

    logger.info("started.")
    em = MailManager()
    # print(list(em.search_email("test", '2026-07-21', '2026-08-13', folder="INBOX")))
    # print(list(em.list_folder()))
    em.cache_message_info("2026-07-21", "2026-08-17", folder="ALL")
    # for m in em.search_email("test", '2026-07-21', '2026-08-13', folder="INBOX"):
    #     print(m)
    #     print(m.get_html())

    # print(em.get_mail_by_uid("489", with_body=True).__next__())
