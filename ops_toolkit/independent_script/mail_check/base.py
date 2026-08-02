#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : test_1
@Author     : LeeCQ
@Date-Time  : 2026/8/1 


"""
import datetime
import io
import json
import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import IO

from mail_manager import MailManager, Mail

logger = logging.getLogger(__name__)


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
        _fhs = json.loads(Path(__file__).parent.joinpath(f"holiday_{_year}.json").read_text(encoding="utf-8"))

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


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_row = False  # 是否处于 <tr>
        self.in_cell = False  # 是否处于 <td>/<th>
        self.current_row = []  # 当前行单元格文本
        self.table_data = []  # 最终全部行元组

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_row = True
            self.current_row = []
        elif tag in ("td", "th"):
            self.in_cell = True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.in_cell = False
        elif tag == "tr":
            self.in_row = False
            # 当前行转为元组存入结果
            self.table_data.append(tuple(self.current_row))

    def handle_data(self, data):
        if self.in_cell:
            # 清理空白、换行
            text = data.strip()
            if text:
                self.current_row.append(text)


class BaseCheck:

    def __init__(self, today=None, cache_db=None):
        self.mail_manager = MailManager(cache_db=Path(__file__).parent / "mail_manager_gtjas.db")
        self.trade_status = TradeDate(today)
        self.assert_name = None

    def get_mail(self, subject, time_start, time_end, **kwargs):
        mail = self.mail_manager.search_email(subject, time_start, time_end, **kwargs)

        self.check_true(mail, "")
        if mail:
            logger.info(f"找到邮件：{mail.subject} 发送时间：{mail.get_send_time().strftime('%Y-%m-%d %H:%M:%S')}")
            return mail
        else:
            raise FileNotFoundError(f"[检查不通过] 易盛北斗星托管系统早盘检查报告 未找到")

    def findstr(self, pat, text):
        rows = re.findall(pat, text)
        logger.debug(f"匹配到行： {rows}")
        return rows

    def docx_to_text(self, doc: bytes | Path | str | IO[bytes]) -> str:
        """将Docx解析为text"""
        from docx2txt import process

        if isinstance(doc, bytes):
            doc = io.BytesIO(doc)
        elif isinstance(doc, Path | str):
            doc = io.open(doc, encoding="utf-8")
        elif isinstance(doc, io.BytesIO):
            pass
        else:
            raise ValueError()

        return process(doc)

    def html_table_to_tuples(self, html: str) -> list[tuple]:
        parser = TableParser()
        parser.feed(html)
        return parser.table_data

    def check_true(self, expr, msg=None):
        if not expr:
            logger.info(self.assert_name + msg)

    def check_equal(self, expr, ex, msg=None):
        """"""


class Test0800(BaseCheck):

    def main(self):
        for c in [self.t_yishen,
                  self.t_aml,
                  self.t_sas_check,
                  self.t_daily_push_log,
                  ]:
            try:
                c()
            except Exception as e:
                logger.error(str(e), exc_info=e)

    def t_yishen(self):
        logger.info("Part 1 Step 6: 易盛北斗星托管系统早盘检查报告")
        mail = self.get_mail(
            f"易盛北斗星托管系统早盘检查报告_国泰君安香港_{self.trade_status.current.strftime('%Y%m%d')}",
            self.trade_status.current.strftime('%Y-%m-%d'),
            self.trade_status.current.strftime('%Y-%m-%d'),
        )

        doc_text = self.docx_to_text(mail.get_attachment())
        if re.findall("异常|提醒", doc_text).__len__() == 2:
            logger.info("[检查通过] 易盛北斗星托管系统早盘检查报告 正常。")
        else:
            logger.error("[检查不通过] 易盛北斗星托管系统早盘检查报告 中 「异常|提醒」 中的数量不符合期望值，请检查。")

    def t_aml(self):
        logger.info("Part 1 Step 9: 邮件检查：Job: [AML Full Batch] Status [Completed]")

        mail = self.get_mail(
            f"[{self.trade_status.last_date_hk.strftime('%Y%m%d')}] Job: [AML Full Batch] Status [Completed]",
            self.trade_status.last_date_hk.strftime('%Y-%m-%d'),
            self.trade_status.current.strftime('%Y-%m-%d'),
        )

    def t_sas_check(self):
        logger.info("Part 1 Step 9: 邮件检查：Job: SAS-Name Check - Job Execution Success")

        mail = self.get_mail(
            f"Date: [{self.trade_status.current.strftime('%Y%m%d')}] SAS-Name Check - Job Execution Success",
            self.trade_status.current.strftime('%Y-%m-%d'),
            self.trade_status.current.strftime('%Y-%m-%d'),
        )

    def t_daily_push_log(self):
        logger.info("Part 1 Step 10: 06:30 Daily Push Log Checking")

        mail = self.get_mail(
            "Daily PushLog Checking",
            self.trade_status.current.strftime('%Y-%m-%d 06:29'),
            self.trade_status.current.strftime('%Y-%m-%d 06:32'),
        )
        err_mgs = []

        # <td>(OCG Dealer)</td><td>(\d{8})</td><td>(.{19}).*?</td></tr>
        ocg = re.findall(r'<td>(OCG Dealer)</td><td>(\d{8})</td><td>(.{16}).*?</td>', mail.get_html())
        logger.info(f"BSS Logon Date匹配到行：{ocg}")
        if not ocg:
            err_mgs.append(f"BSS Logon Date 正则匹配失败。")
        else:
            _hk_last_trade = self.trade_status.last_date_hk.strftime('%Y%m%d')
            if ocg[0][1] != _hk_last_trade:
                err_mgs.append(f"BSS Logon Date: LastLogonDate 错误，期望值={_hk_last_trade} 实际值={ocg[0][1]}")

            _send_time = self.trade_status.current.strftime('%Y-%m-%dT06:30')
            if ocg[0][2] != _send_time:
                err_mgs.append(f"BSS Logon Date: Sending at Time 错误，期望值={_send_time} 实际值={ocg[0][2]}")

        _ldc = self.findstr(r'<tr><td>Last Dayend Completed.*?</td><td>(\d+) (\w+)</td>', mail.get_html())
        if _ldc and _ldc[0][0] == self.trade_status.last_date_hk.strftime('%Y%m%d') and _ldc[0][1] == "Yes":
            logging.info(f"Daily OCG Summary: Last Dayend Completed: 正确 {_ldc[0]}")
        else:
            err_mgs.append(f"BSS Logon Date: LastLogonDate 错误，"
                           f"期望值={self.trade_status.last_date_hk.strftime('%Y%m%d')} Yes "
                           f"实际值={_ldc[0]}")

        _cld = self.findstr(r'<tr><td>Coming Logon Date</td><td>(\d+)</td>', mail.get_html())
        if _cld and _cld[0].strip() == self.trade_status.current.strftime('%Y%m%d'):
            logging.info(f"Daily OCG Summary: Coming Logon Date: 正确 {_cld[0]}")
        else:
            err_mgs.append(f"BSS Logon Date: Coming Logon Date 错误，"
                           f"期望值={self.trade_status.current.strftime('%Y%m%d')} "
                           f"实际值={_cld[0]}")

        for mk, cg, stat in re.findall(r'<td>(HKG)</td><td>(\w*?)\W*?</td><td>(\w{2})</td></tr>', mail.get_html()):
            logger.info(f"HKG and CSC Market Status 匹配到行： {mk} {cg} {stat}")
            if cg in ('ETS', 'GEM', 'MAIN', 'NASD') and stat != 'NO':
                err_mgs.append(
                    f"HKG and CSC Market Status: 匹配失败：Market={mk} Category={cg} 期望状态=NO 实际状态={stat}"
                )

        datafeed_records = self.findstr(r'<tr><td>(HKG|SHA|SZA|188.*?|81.*?)</td><td>(\d+)</td></tr>', mail.get_html())
        if len(datafeed_records) != 15: err_mgs.append(
            f"No of DataFeed Record: 数据匹配不完整， 期望 15 行, 实际 {len(datafeed_records)} 行"
        )
        for mk, record in datafeed_records:
            logger.debug(f"No of DataFeed Record 匹配到行： {mk=} {record=}")
            if mk not in ('188 IndexData', "81 IndexData") and record == "0":
                err_mgs.append(f"No of DataFeed Record: 记录值不正确， 期望值!=0, 实际值={record}")

        if err_mgs:
            logger.error(
                "[检查失败] Part 1 Step 10: 06:30 Daily Push Log Checking：\n> " + "\n> ".join(err_mgs)
            )


class Test0815(BaseCheck):

    def main(self):
        for c in [self.t_tp1_bix_check, self.t_tp1_mds_check, self.t_tp1_fo_mk
                  ]:
            try:
                c()
            except Exception as e:
                logger.error(str(e), exc_info=e)

    def t_tp1_bix_check(self):
        logger.info(
            "Part 1 Step 12: 08:15 TTL Securities FO BIX Check (Email: TP1 PROD-Health Check Notification-PROD)"
        )
        mail = self.get_mail(
            "TP1 PROD-Health Check Notification-PROD",
            self.trade_status.current.strftime('%Y-%m-%d 08:15'),
            self.trade_status.current.strftime('%Y-%m-%d 08:16'),
            mail_id="TTLA5"
        )
        err_mgs = []
        # open("TP1 PROD-Health Check Notification-PROD.html", "w").write(mail.get_html())
        _gs = self.findstr(
            r'<tr><td>(BIX-\w+)</td><td>(.*?)</td><td>(\d+)</td><td>(TRUE|FALSE)</td><td>(TRUE|FALSE)</td><td>.*?</td><td>.*?</td></tr>',
            mail.get_html())
        if len(_gs) != 9: err_mgs.append(
            f"BIX Gateway Status: 数据匹配不完整， 期望 15 行, 实际 {len(_gs)} 行"
        )
        for bid, ip, port, conn, logon in _gs:
            logger.debug(f"No of DataFeed Record 匹配到行： {bid, ip, port, conn, logon}")
            if (bid == 'BIX-FIXOVN' and conn != "TRUE") or (conn != "TRUE" and logon != "TRUE"):
                err_mgs.append(f"No of DataFeed Record: {bid} 记录值不正确， 期望值=TRUE, 实际值={conn}")

        if err_mgs:
            logger.error(
                "[检查失败] Part 1 Step 10: 06:30 Daily Push Log Checking：\n> " + "\n> ".join(err_mgs)
            )

    def t_tp1_mds_check(self):
        logger.info(
            "Part 1 Step 13: 08:15 TTL Secutiries FO MDS Check (Email: TP1 PROD-Health Check Notification-PROD)"
        )
        mail = self.get_mail(
            "TP1 PROD-Health Check Notification-PROD",
            self.trade_status.current.strftime('%Y-%m-%d 08:15'),
            self.trade_status.current.strftime('%Y-%m-%d 08:16'),
            mail_id="TTLA5"
        )
        _mds = self.findstr(
            r'<tr><td>(SERVER)</td><td>(LXPRDTTLA11.*?)</td><td>(\d+)</td><td>(TRUE|FALSE)</td><td>(.*?)</td></tr>',
            mail.get_html())
        if _mds and _mds[0][3] == "TRUE":
            logging.info(f"08:15 TTL Secutiries FO MDS Check: 正确 {_mds[0]}")
        else:
            logging.error(f"08:15 TTL Secutiries FO MDS Check: MDS连接失败"
                          f"期望值=TRUE "
                          f"实际值={_mds[0][3]}")

    def t_tp1_fo_mk(self):
        logger.info(
            "Part 1 Step 14: 08:15 TTL Securities FO Market Info Check (Email: TP1 PROD-Health Check Notification-PROD)"
        )
        mail = self.get_mail(
            "TP1 PROD-Health Check Notification-PROD",
            self.trade_status.current.strftime('%Y-%m-%d 08:15'),
            self.trade_status.current.strftime('%Y-%m-%d 08:16'),
            mail_id="TTLA5"
        )

        err_mgs = []

        # Trading Session Status
        # open("TP1 PROD-Health Check Notification-PROD.html", "w").write(mail.get_html())
        _tss = self.findstr(
            r'<tr><td>(\w+)</td><td>(\w+)</td><td>\w*?</td><td>(TRUE|FALSE)</td></tr>',
            mail.get_html())
        if len(_tss) != 31: err_mgs.append(
            f"Trading Session Status: 数据匹配不完整， 期望 31 行, 实际 {len(_tss)} 行"
        )
        for mt, bid, stat in _tss:
            logger.debug(f"No of DataFeed Record 匹配到行： {mt, bid, stat}")
            if stat != "TRUE" and mt in []: # TODO
                err_mgs.append(f"No of DataFeed Record: {mt} {bid} 记录值不正确， 期望值=TRUE, 实际值={stat}")

        _mi = self.findstr(
            r'<tr><td>(\w+)</td><td>(.{10})</td><td>(.{10})</td><td>(TRUE|FALSE)</td><td>(TRUE|FALSE)</td><td>(TRUE|FALSE)</td><td>(TRUE|FALSE)</td></tr>',
            mail.get_html()
        )
        if len(_mi) != 25: err_mgs.append(
            f"Trading Session Status: 数据匹配不完整， 期望 25 行, 实际 {len(_mi)} 行"
        )
        for mt, mtd, cd, _, login, resu , _ in _mi:
            logger.debug(f"No of DataFeed Record 匹配到行： {mt, mtd, cd, login, resu}")
            if stat != "TRUE" and mt in []: # TODO
                err_mgs.append(f"No of DataFeed Record: {mt} {bid} 记录值不正确， 期望值=TRUE, 实际值={stat}")


        if err_mgs:
            logger.error(
                "[检查失败] Part 1 Step 10: 06:30 Daily Push Log Checking：\n> " + "\n> ".join(err_mgs)
            )
        else:
            logger.info(f"[检查成功] Part 1 Step 10: 06:30 Daily Push Log Checking.")

    def t_tp1_mq(self):
        logger.info(
            "Part 1 Step 15: 08:15 TTL Securities FO MQ Connection Check (Email: TP1 PROD-Health Check Notification-PROD)"
        )
        mail = self.get_mail(
            "TP1 PROD-Health Check Notification-PROD",
            self.trade_status.current.strftime('%Y-%m-%d 08:15'),
            self.trade_status.current.strftime('%Y-%m-%d 08:16'),
            mail_id="TTLA5"
        )
        err_mgs = []
        _mq = self.findstr(
            r'<tr><td>\[(\d+\.\d+\.\d+\.\d+)]:5701</td><td>(\w+)</td></tr>'
        )
        if len(_mq) != 2: err_mgs.append(
            f"MQ Connection: 数据匹配不完整， 期望 2 行, 实际 {len(_mq)} 行"
        )
        for ip, stat in _mq:
            logger.debug(f"MQ Connection: 匹配到行： {ip, stat}")
            if stat != "Active":
                err_mgs.append(f"MQ Connection: {ip} 记录值不正确， 期望值=Active, 实际值={stat}")