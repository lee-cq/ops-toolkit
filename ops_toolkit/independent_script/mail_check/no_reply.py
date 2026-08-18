#!/bin/env python3
""" """
import json
import logging
import sys
import os

import re
from datetime import datetime, date
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "deps"))

from mail_manager import MailManager
from utils import SCRIPT_DIR

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

    def update_status(self, status: str, msg: str = ""):
        self.status = status
        self.msg = msg
        (logger.error if status == "NO_REPLY" else logger.info)(
            f"{self.status}：{self.subject} - {self.msg} ..."
        )

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "subject": self.subject,
            "send_time": self.send_time,
            "to": self.to,
            "cc": self.cc,
            "body": self.body,
            "status": self.status,
            "msg": self.msg,
        }


class MailNotReply:

    def __init__(self, today: str = None, cache_db=None):
        self.today = today or date.today().strftime("%Y-%m-%d")
        self.mail_manager = MailManager(cache_db=cache_db)
        self.folder = os.getenv("NO_REPLAY_FOLDER", "InBox")
        self.report_path = SCRIPT_DIR.joinpath("./reports")
        logger.debug(f"{self.folder=}")
        self.cache_now()
        self.black_subjects = [
            'Daily Operations Completed***',
            'Daily Operations Completed ***',
            'Operations Completed ***',
            'Trade Approval for SIN Market',
            '[LOW] [4102_WAF Suspicious File Extension Access] TrustCSI Security Incident Notification',
            '[MEDIUM] [4136_Detection of abnormal Active Directory account failed to login] TrustCSI Security Incident Notification'
        ]  # 黑名单
        self.black_mailbox = [
            "etradepro@gtjas.com.hk"
        ]
        self.retail_mails = []  # Retail成员
        self.reports = []

        self.checker()
        self.notify()

    def cache_now(self):
        """"""
        logger.info("Cache Today mails.")
        if not DEBUG:
            self.mail_manager.cache_message_info(
                self.today, self.today, folder=self.folder, with_body=True
            )

    @staticmethod
    def is_black(sub, blacks: list) -> bool:
        """"""
        for _ in blacks:
            if _ in sub:
                return True
        return False

    def report(self):
        self.report_path.joinpath(f"no_reply_mail_{self.today}.html").write_text(
            SCRIPT_DIR.joinpath("./template_report_no_reply_mail.html").read_text(
                encoding="utf-8"
            ).replace(
                "__ROW_REPORTS_JSON__",
                self.report_path.joinpath(f"no_reply_mail_{self.today}.json").read_text(encoding="utf-8"),
            ),
            encoding="utf-8"
        )

    def notify(self):
        """"""
        logger.info("==== Reports =====")
        _no_reply = "\n".join((
                                  f"{i + 1: 3d}. {m.subject}\n"
                                  f"    sender: {m.sender}\n"
                                  f"    send_time: {m.send_time}"
                              ) for i, m in enumerate(m for m in self.reports if m.status == "NO_REPLY"))
        logger.warning(f"{self.today} 未回复邮件：\n" + _no_reply)
        self.report_path.joinpath(
            f"no_reply_mail_{self.today}.json"
        ).write_text(
            json.dumps([_.to_dict() for _ in self.reports], indent=4, ensure_ascii=False),
            encoding="utf-8"
        )
        self.report()

    def checker(self):
        _where_sender_sot = f"AND sender in (" + ", ".join(f"'{_}'" for _ in self.retail_mails) + ")"
        from html2txt import html2text
        for retail_mail in self.mail_manager.search_email(
                "", self.today, self.today, folder=self.folder,
                recipients="it.retail@gtjas.com.hk"):
            logger.debug("### New Email Found.")
            logger.debug(f"Found Mail: {retail_mail.subject}, sender={retail_mail.sender}")

            m_body: str = "\n".join(retail_mail.body.values()) if isinstance(retail_mail.body, dict) else str(
                retail_mail.body)
            _r = Report(
                sender=retail_mail.sender,
                subject=retail_mail.subject,
                send_time=retail_mail.get_send_time().strftime("%Y-%m-%d %H:%M"),
                to=retail_mail.recipients,
                cc=retail_mail.cc,
                body=html2text(retail_mail.get_html()),
                status="",
            )
            self.reports.append(_r)
            # if retail_mail.sender in (
            #         'soc@citictel-cpc.com'
            # ):
            #     continue
            pattern = r"(Hi|Hello|Dear)\s+(gtja|gtjai|retail|support|team|application team|Customer|IT Team|all)[,:\n\t\r]"
            if not re.search(
                    pattern,
                    m_body,
                    flags=re.I,
            ):
                _r.update_status("skip", "mail no have Hi team|grja")
                continue

            if self.is_black(retail_mail.subject, self.black_subjects):
                _r.update_status("skip", "subject 在黑名单中")
                continue

            if self.is_black(retail_mail.sender, self.black_mailbox):
                _r.update_status("skip", "sender 在黑名单中")
                continue

            for soa_sender in self.retail_mails:
                if self.mail_manager.search_email_newest(
                        retail_mail.subject,
                        retail_mail.get_send_time(),
                        datetime.now(),
                        folder=self.folder,
                        sender=soa_sender):
                    _r.update_status("replied", f"邮件已由 「{soa_sender}」回复。")
                    break
            else:
                # self.no_reply_mails.append(retail_mail)
                _r.update_status("NO_REPLY", "邮件未回复")
                # logger.error(f"邮件未回复：「{retail_mail.subject}」")


def main():
    logger.debug("STARTED.")
    from utils import load_env
    load_env()
    MailNotReply(
        today=date(2026, 8, 11).strftime("%Y-%m-%d"),
        cache_db="./cache_retail-not-replay.db",
    )


if __name__ == "__main__":
    DEBUG = True
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s",
        encoding="utf-8",
    )
    main()
