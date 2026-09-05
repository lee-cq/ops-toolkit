#!/bin/env python3
""" """

import json
import logging
import sys
import os

import re
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "deps"))

from html2txt import html2text

from mail_manager import MailManager, Mail
from utils import SCRIPT_DIR

logger = logging.getLogger(__name__)
DEBUG = False


@dataclass
class Report:
    sender: str
    subject: str
    send_time: str
    to: str
    cc: str
    body: str

    status: str
    msg: str = ""
    thread_emails: list[Mail] = None

    def update_status(self, status: str, msg: str = ""):
        self.status = status
        self.msg = msg
        (logger.error if status == "NO_REPLY" else logger.info)(
            f"{self.status}：{self.subject} - {self.msg} ..."
        )

    def to_dict(self) -> dict:
        if self.thread_emails is None:
            self.thread_emails = []
        return {
            "sender": self.sender,
            "subject": self.subject,
            "send_time": self.send_time.strftime("%Y-%m-%d %H:%M"),
            "to": self.to,
            "cc": self.cc,
            "body": self.body,
            "status": self.status,
            "msg": self.msg,
            "thread_emails": [
                {
                    "sender": m.sender,
                    "subject": m.subject,
                    "send_time": m.get_send_time().strftime("%Y-%m-%d %H:%M"),
                    "to": m.recipients,
                    "cc": m.cc,
                    "body": html2text(m.get_html()),
                }
                for m in self.thread_emails
            ],
        }


@dataclass
class BlackItem:
    name: str = ""
    subject: str | None = ""
    sender: str | None = ""
    body: str | None = ""

    def is_black(self, mail: Mail) -> str:
        """"""
        if not self.name:
            self.name = "Black Rule Name Not Set"            
        
        _rst = all(
            re.search(_r, _s, flags=re.I)
            for _r, _s in (
                (self.subject, mail.subject),
                (self.sender, mail.sender),
                (self.body, html2text(mail.get_html())),
            ) if _r
        )
        logger.debug(f"BLACK CHECK: [{_rst}]: {self.name}")
        return self.name if _rst else ""
        if self.subject and re.search(self.subject, mail.subject, flags=re.I):
            return self.name
        if self.sender and re.search(self.sender, mail.sender, flags=re.I):
            return self.name
        if self.body and re.search(self.body, html2text(mail.get_html()), flags=re.I):
            return self.name
        return ""


class Blacklist:
    def __init__(self, bks: list[dict[str, str]]):
        self.items: list[BlackItem] = [BlackItem(**d) for d in bks]

    def in_blacklist(self, mail: Mail) -> str:
        for bi in self.items:
            if name := bi.is_black(mail):
                return name
        return ""


class MailNotReply:

    def __init__(self, today: str = None, cache_db=None):
        self.today = today or date.today().strftime("%Y-%m-%d")
        self.mail_manager = MailManager(cache_db=cache_db)
        self.folder = os.getenv("NO_REPLAY_FOLDER", "InBox")
        self.report_path = SCRIPT_DIR.joinpath("./reports")
        logger.debug(f"{self.folder=}")
        self.cache_now()
        self.bkl = Blacklist(
            json.loads(
                SCRIPT_DIR.joinpath("no_reply_config.json").read_text(encoding="utf8")
            )["blacklist"]
        )
        self.retail_mails = json.loads(
            SCRIPT_DIR.joinpath("no_reply_config.json").read_text(encoding="utf8")
        )["retail_member"]
        self.reports = []

        self.checker()
        self.notify()

    def cache_now(self):
        """"""
        logger.info("Cache Today mails.")
        _st = datetime.strptime(self.today, "%Y-%m-%d")
        _et = min(datetime.now(), _st + timedelta(days=10))
        if not DEBUG:
            self.mail_manager.cache_message_info(
                _st, _et, folder=self.folder, with_body=True
            )
        else:
            logger.warning("NOW DEBUGGING, NOT CACHE MAILS.")

    @staticmethod
    def is_black(sub, blacks: list) -> bool:
        """"""
        for _ in blacks:
            if _ in sub:
                return True
        return False

    def report(self):
        self.report_path.joinpath(f"no_reply_mail_{self.today}.html").write_text(
            SCRIPT_DIR.joinpath("./template_report_no_reply_mail.html")
            .read_text(encoding="utf-8")
            .replace(
                "__ROW_REPORTS_JSON__",
                self.report_path.joinpath(f"no_reply_mail_{self.today}.json").read_text(
                    encoding="utf-8"
                ),
            ),
            encoding="utf-8",
        )

    def notify(self):
        """"""
        logger.info("==== Reports =====")
        _no_reply = "\n".join(
            (
                f"{i + 1: 3d}. {m.subject}\n"
                f"    sender: {m.sender}\n"
                f"    send_time: {m.send_time}"
            )
            for i, m in enumerate(m for m in self.reports if m.status == "NO_REPLY")
        )
        logger.warning(f"{self.today} 未回复邮件：\n" + _no_reply)
        self.report_path.joinpath(f"no_reply_mail_{self.today}.json").write_text(
            json.dumps(
                [_.to_dict() for _ in self.reports], indent=4, ensure_ascii=False
            ),
            encoding="utf-8",
        )
        self.report()

    def checker(self):
        logger.info("=" * 30)
        logger.info(f"{'start check':^30}")
        logger.info("=" * 30)
        _sql_retail_mails = ", ".join(f"'{m}'" for m in self.retail_mails)
        _sql_not_retail = (
            " AND ( "
            + " OR ".join(f"sender NOT LIKE '%{m}%' " for m in self.retail_mails)
            + " ) "
        )
        _sql_in_retail = (
            " AND ( "
            + " OR ".join(f"sender LIKE '%{m}%' " for m in self.retail_mails)
            + " ) "
        )
        _to_retail_total = 0

        for retail_mail in self.mail_manager.search_email(
            "",
            self.today,
            self.today,
            folder=self.folder,
            recipients="it.retail@gtjas.com.hk",
            where_sql=_sql_not_retail,
            _recached=True,
        ):
            _to_retail_total += 1
            logger.debug(f"### New Email Found, {_to_retail_total=}")

            logger.debug(
                f"Found Mail: {retail_mail.subject}, sender={retail_mail.sender}"
            )

            m_body: str = (
                "\n".join(retail_mail.body.values())
                if isinstance(retail_mail.body, dict)
                else str(retail_mail.body)
            )
            _r = Report(
                sender=retail_mail.sender,
                subject=retail_mail.subject,
                send_time=retail_mail.get_send_time(),
                to=retail_mail.recipients,
                cc=retail_mail.cc,
                body=html2text(retail_mail.get_html()),
                status="",
                thread_emails=list(
                    self.mail_manager.search_email(
                        retail_mail.subject, self.today, self.today, _recached=True
                    )
                ),
            )
            self.reports.append(_r)
            pattern = r"(Hi|Hello|Dear)?.+?(gtja|gtjai|retail|support|team|application team|Customer|IT Team|all|IT Retail).*?[,:\n\t\r]?"
            if not re.search(
                pattern,
                m_body,
                flags=re.I,
            ):
                _r.update_status("skip", "mail no have Hi team|gtja...")
                continue

            if name := self.bkl.in_blacklist(retail_mail):
                _r.update_status("skip", f"黑名单规则命中：{name}")
                continue

            if senders := ", ".join(
                m.sender
                for m in self.mail_manager.search_email(
                    retail_mail.subject,
                    retail_mail.get_send_time(),
                    datetime.now(),
                    where_sql=_sql_in_retail,
                    _recached=True,
                )
            ):
                _r.update_status("replied", f"邮件已回复\n{senders}")
                continue
            else:
                _r.update_status("NO_REPLY", "邮件未回复")
                # logger.error(f"邮件未回复：「{retail_mail.subject}」")


def main():
    logger.debug("STARTED.")
    from utils import load_env

    load_env()
    MailNotReply(
        today=date(2026, 9, 4).strftime("%Y-%m-%d"),
        cache_db="./cache_retail-not-replay.db",
    )


if __name__ == "__main__":
    DEBUG = False
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s",
        encoding="utf-8",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("log_noreply_test.log", "w", encoding="utf8"),
        ],
    )
    main()
