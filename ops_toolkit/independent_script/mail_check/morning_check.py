#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : morning check
@Author     : LeeCQ
@Date-Time  : 2026/8/1 


"""
import html
import io
import json
import logging
import re
import zipfile
import os
import xml.etree.ElementTree as Et

from datetime import date, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from mail_manager import MailManager, get_imap_from_env
from utils import SCRIPT_DIR

logger = logging.getLogger(__name__)


class TradeDate:

    def __init__(self, date_: date | str = None):
        # 今天日期
        _current = date_ or date.today()
        if not isinstance(_current, date):
            try:
                self.current = date.strptime(_current, "%Y-%m-%d")
            except Exception as e:
                logger.warning(f"日期初始化失败：{self.current}, 「{e}」")
                self.current = date.today()
        else:
            self.current = _current

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
        _fhs = json.loads(SCRIPT_DIR.joinpath(f"holiday_{_year}.json").read_text(encoding="utf-8"))

        if self.current.weekday() > 5:
            self.is_holiday_hk = True
            self.is_holiday_cn = True
        else:
            _ds = self.current.strftime("%Y-%m-%d")
            self.is_holiday_hk = _ds in _fhs["hk"]
            self.is_holiday_cn = _ds in _fhs["cn"]

        self.last_date_hk = self.get_last_trade_date(self.current - timedelta(days=1), _fhs["hk"])
        self.last_date_cn = self.get_last_trade_date(self.current - timedelta(days=1), _fhs["cn"])

    def get_last_trade_date(self, _date: date, holidays: list[str]):
        if _date.weekday() >= 5 or _date.strftime("%Y-%m-%d") in holidays:
            return self.get_last_trade_date(_date - timedelta(days=1), holidays)
        return _date


class Docx2Text(object):
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    def qn(self, tag):
        """        Source: https://github.com/python-openxml/python-docx/        """
        prefix, tagroot = tag.split(':')
        uri = self.nsmap[prefix]
        return '{{{}}}{}'.format(uri, tagroot)

    def xml2text(self, xml):
        """        Adapted from: https://github.com/python-openxml/python-docx/        """
        text = u''
        root = Et.fromstring(xml)
        for child in root.iter():
            if child.tag == self.qn('w:t'):
                t_text = child.text
                text += t_text if t_text is not None else ''
            elif child.tag == self.qn('w:tab'):
                text += '\t'
            elif child.tag in (self.qn('w:br'), self.qn('w:cr')):
                text += '\n'
            elif child.tag == self.qn("w:p"):
                text += '\n\n'
        return text

    def process(self, docx, img_dir=None):
        text = u''

        # unzip the docx in memory
        zipf = zipfile.ZipFile(docx)
        filelist = zipf.namelist()

        # get header text
        # there can be 3 header files in the zip
        header_xmls = 'word/header[0-9]*.xml'
        for f_name in filelist:
            if re.match(header_xmls, f_name):
                text += self.xml2text(zipf.read(f_name))

        # get main text
        doc_xml = 'word/document.xml'
        text += self.xml2text(zipf.read(doc_xml))

        # get footer text
        # there can be 3 footer files in the zip
        footer_xmls = 'word/footer[0-9]*.xml'
        for f_name in filelist:
            if re.match(footer_xmls, f_name):
                text += self.xml2text(zipf.read(f_name))

        if img_dir is not None:
            # extract images
            for f_name in filelist:
                _, extension = os.path.splitext(f_name)
                if extension in [".jpg", ".jpeg", ".png", ".bmp"]:
                    Path(img_dir).joinpath(
                        zipfile.Path(f_name).name
                    ).write_bytes(zipf.read(f_name))
                    # dst_f_name = os.path.join(img_dir, os.path.basename(f_name))
                    # with open(dst_f_name, "wb") as dst_f:
                    #     dst_f.write(zipf.read(f_name))

        zipf.close()
        return text.strip()


@dataclass
class CheckStatus:
    name: str
    status: bool
    actual: str
    expected: str
    msg: str

    def to_readable(self):
        return (
            "✅" if self.status else "❌", self.name, self.actual, self.expected, self.msg
        )

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "actual": self.actual,
            "expected": self.expected,
            "msg": self.msg
        }


@dataclass
class Step:
    part: int
    step: int
    name: str

    #
    reports: list[CheckStatus] = field(default_factory=list)

    _reported = False

    def __str__(self):
        return f"Part {self.part} Step {self.step:02d}: {self.name}"

    def __del__(self):
        self.to_reports()

    def add_report(self, name: str, status: bool, actual: str, expected: str, msg: str = ""):
        self.reports.append(
            CheckStatus(
                name=name,
                status=status,
                actual=actual,
                expected=expected,
                msg=msg
            )
        )
        if status:
            logger.info(
                f"✅ 检查通过: {self} : {name} "
            )
        else:
            logger.error(
                f"❌ 检查失败: {self} : {name} - 期望值： [{expected}], 实际值: [{actual}] ; ({msg})"
            )

    @property
    def status(self) -> bool:
        return all(_.status for _ in self.reports)

    @property
    def count_errors(self) -> int:
        return sum(1 for _ in self.reports if _.status)

    @property
    def report_errors(self) -> str:
        return "\n".join(
            f"❌ {_.name} 期望值： [{_.expected}], 实际值: [{_.actual}] ; ({_.msg})"
            for _ in self.reports if not _.status
        )

    @property
    def report_step(self) -> str:
        _st = "✅" if self.status else "❌"
        return f"{_st} {self.__str__()}" + (f"\n{self.report_errors}" if self.report_errors else "") + "\n"

    @classmethod
    def from_reports(cls, raw_name, reports):
        part, step, name = re.findall(r"Part (\d) Step (\d+): (.*)", raw_name)[0]
        self = cls(part=int(part), step=int(step), name=name)
        self._reported = True
        for i in reports:
            self.reports.append(CheckStatus(**i))

        return self

    def to_reports(self, file=None):
        """将内容追加到报告中"""
        if self._reported:
            return
        self._reported = True

        file = Path(file) if file else SCRIPT_DIR.joinpath(
            f"reports_{date.today().strftime('%Y-%m-%d')}.json")
        file.parent.mkdir(parents=True, exist_ok=True)

        _ds = json.load(file.open(encoding="utf-8")) if file.exists() else {}
        _ds[self.__str__()] = [_.to_dict() for _ in self.reports]
        file.write_text(
            json.dumps(
                _ds,
                ensure_ascii=False,
                indent=2,
                sort_keys=False,
            ),
            encoding="utf8"
        )
        logger.info(f"保存到Report({file.name})成功: {self}")


# noinspection DuplicatedCode
class MorningCheck:

    def __init__(self, today=None, cache_db=None):
        imap = get_imap_from_env() if os.environ.get("IMAP_HOST") else None

        self.report_path = SCRIPT_DIR.joinpath("reports")
        self.reports = []
        self.mail_manager = MailManager(imap=imap, cache_db=cache_db)
        self.today = today if isinstance(today, str) else (today or date.today()).strftime('%Y-%m-%d')
        self.trade_date = TradeDate(self.today)
        self.assert_name = None

    def report(self):
        """"""

        self.report_path.mkdir(parents=True, exist_ok=True)
        self.report_path.joinpath(f"morning_check_{self.today}.html").write_text(
            SCRIPT_DIR.joinpath("./template_report_morning_check.html").read_text(
                encoding="utf-8"
            ).replace(
                "__ROW_REPORTS_JSON__",
                self.report_path.joinpath(f"morning_check_{self.today}.json").read_text(encoding="utf-8"),
            ).replace(
                "__REPORT_DATE__",
                self.today
            ),
            encoding="utf-8"
        )

    def report_to_mail(self):
        from mail_manager import send_email
        if not os.getenv("MORNING_CHECK_MAIL_TO", ""):
            logger.warning("没有配置收件人，无法发送邮件")
            return
        self.report()
        _rps = [Step.from_reports(*_) for _ in
                json.loads(
                    self.report_path.joinpath(f"morning_check_{self.today}.json").read_text(encoding="utf-8")).items()
                ]
        if send_email(
                None,
                f"[Try-Run] Morning Check Report [Mail Part] - {self.today}",
                "\n".join(_.report_step for _ in _rps) + "\n\n检查细节见附件",
                atta=self.report_path.joinpath(f"morning_check_{self.today}.html"),
                to=os.getenv("MORNING_CHECK_MAIL_TO", ""),
                cc=os.getenv("MORNING_CHECK_MAIL_CC", ""),
        ):
            logger.info("Email Sent Successfully.")
        else:
            logger.info("Email Sent Failed.")

    def report_to_teams(self):
        pass

    def get_mail(self, subject, time_start, time_end, /, step: Step, msg="", **kwargs):
        folder = os.getenv("MORNING_CHECK_FOLDER", "InBox")
        try:
            mail = self.mail_manager.search_email_newest(subject, time_start, time_end, folder=folder, **kwargs)
        except Exception as e:
            logger.error(e)
            mail = None

        time_start, time_end = self.mail_manager.verify_query_time(time_start, time_end)
        time_start = time_start.strftime('%Y-%m-%d %H:%M:%S')
        time_end = time_end.strftime('%Y-%m-%d %H:%M:%S')

        step.add_report(
            "Found Mail",
            bool(mail),
            f"{mail.subject} \n发送时间：{mail.get_send_time().strftime('%Y-%m-%d %H:%M:%S')}" if mail else "未找到邮件",
            f"找到在 {time_start} -- {time_end} 期间发送的邮件：\n{subject} ",
            "检查邮箱中是否收到了邮件" + (f", {msg}" if msg else ""),
        )

        if mail:
            logger.info(f"✅找到邮件：{mail.subject} 发送时间：{mail.get_send_time().strftime('%Y-%m-%d %H:%M:%S')}")
            return mail
        else:
            raise FileNotFoundError(f"❌未找到邮件：{subject} 在 {time_start} -- {time_end} 期间")

    @staticmethod
    def findstr(pat, text, _s: Step = None, name="", less_len=1):
        """f
        :args 模式，str, Step, name, 期望数量
        :returns

        """
        rows = re.findall(pat, text, flags=re.I | re.M)
        logger.debug(f"匹配到行： {rows}")
        if len(rows) < less_len and _s:
            logger.info(f"RE PATTERN: {pat}")
            _s.add_report(
                name,
                len(rows) >= less_len,
                len(rows).__str__(), less_len.__str__(),
                "正则匹配数量不足, 需人工确认，并检查自动化代码"
            )
        return rows

    @staticmethod
    def docx_to_text(doc: bytes | Path | str | IO[bytes]) -> str:
        """将Docx解析为text"""

        if isinstance(doc, bytes):
            doc = io.BytesIO(doc)
        elif isinstance(doc, Path | str):
            doc = io.open(doc, encoding="utf-8")
        elif isinstance(doc, io.BytesIO):
            pass
        else:
            raise ValueError()

        return Docx2Text().process(doc)

    def _main(self, *args):
        for func in args:
            _s = None
            try:
                _s: Step = func()
                self.reports.append(_s)
            except Exception as e:
                logger.error(func.__name__ + ": " + str(e))
            finally:
                if isinstance(_s, Step):
                    _s.to_reports(self.report_path.joinpath(f"morning_check_{self.today}.json"))

    def main_0800(self):
        self._main(
            self.check_1_06_esunny,
            self.check_1_09_aml_sas,
            self.check_1_10_0630_daily_push_log_hkg_status_no,
        )

    def main_0818(self):
        self._main(
            self.check_1_11_tp1_bix_gateway_status,
            self.check_1_12_tp1_mds_status,
            self.check_1_13_tp1_external_bix_status,
            self.check_1_14_tp1_fo_market_info,
            self.check_1_15_tp1_mq,
            self.check_1_18_daily_pushlog,
        )

    def main_0836(self):
        self._main(
            self.check_1_21_daily_instrument_changed,
        )

    def main_0901(self):
        self._main(
            self.check_2_2_0901_daily_pushlog_order_status
        )

    def main_0916(self):
        self._main(
            self.check_3_2_kstar_quotes_started,
            self.check_3_3_exec_job_status,
            self.check_3_4_trade_data_capture
        )

    def check_1_06_esunny(self) -> Step:
        _s = Step(1, 6, "易盛北斗星托管系统早盘检查报告")
        logger.info(f"Start Check: {_s}")
        mail = self.get_mail(
            f"易盛北斗星托管系统早盘检查报告_国泰君安香港_{self.trade_date.current.strftime('%Y%m%d')}",
            self.trade_date.current.strftime('%Y-%m-%d'),
            self.trade_date.current.strftime('%Y-%m-%d'),
            _s
        )

        counts_ok = self.findstr("正常|忽略", self.docx_to_text(mail.get_attachment())).__len__()
        counts_err = self.findstr("异常|提醒", self.docx_to_text(mail.get_attachment())).__len__()
        _s.add_report(
            "报告中正常或忽略出现的次数 ",
            counts_ok >= 90 and counts_err <= 2,
            f"正常|忽略： {counts_ok}, 错误|提醒: {counts_err}",
            f"正常|忽略： >=90, 错误|提醒: <2"
        )
        return _s

    def check_1_09_aml_sas(self) -> Step:
        _s = Step(1, 9, "邮件检查：AML Full Batch & SAS-Name Check")
        logger.info(_s)

        try:
            t_2 = TradeDate(self.trade_date.last_date_hk)
            td = max(t_2.last_date_cn, t_2.last_date_hk)
            self.get_mail(
                f"[{td.strftime('%Y%m%d')}] Job: [AML Full Batch] Status [Completed]",
                self.trade_date.last_date_hk.strftime('%Y-%m-%d'),
                self.trade_date.current.strftime('%Y-%m-%d'),
                _s, msg=""
            )
        except FileNotFoundError:
            pass
        try:
            self.get_mail(
                f"Date: [{self.trade_date.current.strftime('%Y%m%d')}] SAS-Name Check - Job Execution Success",
                self.trade_date.current.strftime('%Y-%m-%d'),
                self.trade_date.current.strftime('%Y-%m-%d'),
                _s
            )
        except FileNotFoundError:
            pass
        return _s

    def check_1_10_0630_daily_push_log_hkg_status_no(self) -> Step:
        _s = Step(1, 10, "06:30 HKG Trading Status is NO (Not Yet Open)")
        logger.info(_s)

        mail = self.get_mail(
            "Daily PushLog Checking",
            self.trade_date.current.strftime('%Y-%m-%d 06:29'),
            self.trade_date.current.strftime('%Y-%m-%d 06:32'),
            _s
        )

        for mk, cg, stat in self.findstr(
                r'<td>(HKG)</td><td>(\w*?)\W*?</td><td>(\w{2})</td></tr>', mail.get_html(),
                _s, "HKG Market Status 完整性验证", 4
        ):
            logger.debug(f"HKG and CSC Market Status 匹配到行： {mk} {cg} {stat}")
            # if cg in ('ETS', 'GEM', 'MAIN', 'NASD'):
            _s.add_report(
                f"HKG and CSC Market Status (Market = {cg})",
                stat == 'NO', stat, "NO"
            )

        # ===== Have record for DataFeed Record except IndexData =====
        for mk, record in self.findstr(
                r'<tr><td>(HKG|SHA|SZA|188.*?|81.*?)</td><td>(\d+)</td></tr>', mail.get_html(),
                _s, "No of DataFeed Record: 数据匹配完整性", 15
        ):
            logger.debug(f"No of DataFeed Record 匹配到行： {mk=} {record=}")
            if mk in ('188 IndexData', "81 IndexData"):
                _s.add_report(
                    f"No of DataFeed Record: ({mk})",
                    record == "0",
                    record, "0"
                )
            else:
                _s.add_report(
                    f"No of DataFeed Record: ({mk})",
                    int(record) > 0,
                    record, "> 0"
                )

        return _s

    def check_1_11_tp1_bix_gateway_status(self) -> Step:
        _s = Step(1, 11, "08:15 TTL Securities FO BIX Check (Email: TP1 PROD-Health Check Notification-PROD)")
        logger.info(_s)

        mail = self.get_mail(
            "TP1 PROD-Health Check Notification-PROD",
            self.trade_date.current.strftime('%Y-%m-%d 08:15'),
            self.trade_date.current.strftime('%Y-%m-%d 08:16'),
            mail_id="TTLA5",
            step=_s,
        )
        # open("TP1 PROD-Health Check Notification-PROD.html", "w").write(mail.get_html())
        _gs = self.findstr(
            r'<tr><td>(BIX-\w+)</td><td>(.*?)</td><td>(\d+)</td><td>(TRUE|FALSE)</td><td>(TRUE|FALSE)</td><td>.*?</td><td>.*?</td></tr>',
            mail.get_html(), _s, "BIX Gateway Status: 数据匹配完整性", 9
        )
        for bid, ip, port, conn, logon in _gs:
            logger.debug(f"No of DataFeed Record 匹配到行： {bid, ip, port, conn, logon}")
            _s.add_report(
                f"No of DataFeed Record: {bid} ",
                (conn == "TRUE" and logon == "TRUE"),
                # or (bid == 'BIX-FIXOVN' and conn == "TRUE"),
                f"{conn}, {logon}",
                f"connect=TRUE, Logon=True",
                {
                    "BIX-FIXOVN": "通常邮件中是False, 08:30前在 SEC TTL的health Check中再次检查",
                }.get(bid, "")
            )

        return _s

    def check_1_12_tp1_mds_status(self) -> Step:
        _s = Step(1, 12, "08:15 TTL Secutiries FO MDS Check (Email: TP1 PROD-Health Check Notification-PROD)")
        logger.info(_s)
        mail = self.get_mail(
            "TP1 PROD-Health Check Notification-PROD",
            self.trade_date.current.strftime('%Y-%m-%d 08:15'),
            self.trade_date.current.strftime('%Y-%m-%d 08:16'),
            mail_id="TTLA5",
            step=_s,
        )
        _mds = self.findstr(
            r'<tr><td>(SERVER)</td><td>(LXPRDTTLA11.*?)</td><td>(\d+)</td><td>(\w+?)</td><td>(.*?)</td></tr>',
            mail.get_html(), _s, "TP1, MDS Check数据匹配完整性")
        if _mds:
            _s.add_report(
                "TP1, MDS Check",
                bool(_mds[0][3] == "TRUE" and _mds[0][4].replace(" ", "") == "MAMK,USA,SZMK,BOD,HKEX"),
                f"{_mds}",
                "OK / MAMK,USA,SZMK,BOD,HKEX",
                "通常周一没有BOD"
            )
        return _s

    def check_1_13_tp1_external_bix_status(self) -> Step:
        _s = Step(1, 13, "08:15 TTL Sec TP1 External BIX Gateway Status")
        logger.info(_s)
        mail = self.get_mail(
            "TP1 PROD-Health Check Notification-PROD",
            self.trade_date.current.strftime('%Y-%m-%d 08:15'),
            self.trade_date.current.strftime('%Y-%m-%d 08:16'),
            mail_id="TTLA5",
            step=_s,
        )
        for bid in ["BIX-FCFIX2", "BIX-FIXIDM", "BIX-FCFIX"]:
            _g = self.findstr(
                # "<tr><td>({bid})</td><td>LXPRDTTLA13.GTJA.COM.HK</td><td>14900</td><td>TRUE</td><td>FCFIX</td><td>HSR</td></tr>"
                f"<tr><td>({bid})</td><td>(.+?)</td><td>(\\d+)</td><td>(\\w+?)</td><td>(.*?)</td><td>(.*?)</td></tr>",
                mail.get_html(), _s, f"TP1 External BIX Gateway - {bid} 数据匹配完整性"
            )
            if _g:
                _s.add_report(
                    f"TP1 External BIX Gateway - {bid}",
                    _g[0][3] == "TRUE",
                    f"{_g}",
                    "OK / MAMK,USA,SZMK,BOD,HKEX"
                )
        return _s

    def check_1_14_tp1_fo_market_info(self) -> Step:
        _s = Step(1, 14, "08:15 TTL Securities FO Market Info Check (Email: TP1 PROD-Health Check Notification-PROD)")
        logger.info(_s)
        mail = self.get_mail(
            "TP1 PROD-Health Check Notification-PROD",
            self.trade_date.current.strftime('%Y-%m-%d 08:15'),
            self.trade_date.current.strftime('%Y-%m-%d 08:16'),
            mail_id="TTLA5",
            step=_s
        )
        market_info = [
            ("AUS", "CurrentDate/Logon/Resurrect"),
            ("BOND", "CurrentDate/None/Recurrect"),
            ("CAN", "LastTradeDate/Logon/Resurrect"),
            ("CHE", "LastTradeDate/Logon/Resurrect"),
            ("DEU", "LastTradeDate/Logon/Resurrect"),
            ("ELN", "CurrentDate/None/Resurrect"),
            ("FRA", "LastTradeDate/Logon/Resurrect"),
            ("FUND", "CurrentDate/None/Resurrect"),
            ("HKEX", "CurrentDate/Logon"),
            ("JPN", "CurrentDate/Logon/Resurrect"),
            ("KOR", "CurrentDate/Logon/Resurrect"),
            ("MAMK", "CurrentDate/Logon"),
            ("SHB", "CurrentDate/Logon"),
            ("SIN", "CurrentDate/Logon"),
            ("SPMK", "CurrentDate/None/Resurrect"),
            ("SZB", "CurrentDate/Logon"),
            ("SZMK", "CurrentDate/Logon"),
            ("UKG", "LastTradeDate/Logon/Resurrect"),
            ("USA", "LastTradeDate/Logon/Resurrect"),
        ]
        open("tmp.html", 'w', encoding="utf-8").write(mail.get_html())

        def _is_ok(_act: list[str], _exp: str):
            _rst = []
            if "LastTradeDate" in _exp:
                _rst.append(_act[1] == self.trade_date.last_date_hk.strftime('%Y-%m-%d'))
            elif "CurrentDate" in _exp:
                _rst.append(_act[1] == self.trade_date.current.strftime('%Y-%m-%d'))
            if "Logon" in _exp:
                _rst.append(_act[4] == 'TRUE')
            if "Resurrect" in _exp:
                _rst.append(_act[5] == 'TRUE')
            return all(_rst)

        for mk, exp in market_info:
            _g = self.findstr(
                r'<tr><td>(%s)</td><td>(.{10})</td><td>(.{10})</td><td>(TRUE|FALSE)</td><td>(TRUE|FALSE)</td><td>(TRUE|FALSE)</td><td>(TRUE|FALSE)</td></tr>' % mk,
                mail.get_html(), _s, f"{mk}: 数据匹配",
            )
            if _g:
                _s.add_report(
                    mk,
                    _is_ok(_g[0], exp),
                    f"{mk} MarketDate={_g[0][1]} Logon={_g[0][4]} Resurrect={_g[0][5]}",
                    exp
                )

        return _s

    def check_1_15_tp1_mq(self) -> Step:
        _s = Step(1, 15, "08:15 TTL Securities FO MQ Connection Check (Email: TP1 PROD-Health Check Notification-PROD)")
        logger.info(_s)
        mail = self.get_mail(
            "TP1 PROD-Health Check Notification-PROD",
            self.trade_date.current.strftime('%Y-%m-%d 08:15'),
            self.trade_date.current.strftime('%Y-%m-%d 08:16'),
            mail_id="TTLA5",
            step=_s,
        )
        _mq = self.findstr(
            r'<tr><td>\[(\d+\.\d+\.\d+\.\d+)]:5701</td><td>(\w+)</td></tr>',
            mail.get_html(), _s, "TP1 MQ Status - 数据匹配校验"
        )
        if _mq:
            _s.add_report(
                "MQ Connection Status",
                len(_mq) >= 2 and all(_2 == "Active" for _1, _2 in _mq),
                ",".join(f"{_1}({_2})" for _1, _2 in _mq),
                "IP(Active),IP(Active）"
            )
        return _s

    def check_1_18_daily_pushlog(self) -> Step:
        _s = Step(1, 18, "06:30 HKG Trading Status is NO (Not Yet Open)")
        logger.info(_s)

        mail = self.get_mail(
            "Daily PushLog Checking",
            self.trade_date.current.strftime('%Y-%m-%d 06:29'),
            self.trade_date.current.strftime('%Y-%m-%d 06:32'),
            _s
        )

        # =========Last Logon date time is current trading date =====================
        # <td>(OCG Dealer)</td><td>(\d{8})</td><td>(.{19}).*?</td></tr>
        ocg = self.findstr(r'<td>(OCG Dealer)</td><td>(\d{8})</td><td>(.{16}).*?</td>', mail.get_html(),
                           _s, "BSS Logon Date 正则匹配失败"
                           )
        if ocg:
            _hk_last_trade = self.trade_date.last_date_hk.strftime('%Y%m%d')
            _s.add_report(
                "BSS Logon Date: LastLogonDate",
                ocg[0][1] == _hk_last_trade,
                ocg[0][1],
                _hk_last_trade,
                ""
            )

            _send_time = self.trade_date.current.strftime('%Y-%m-%dT06:30')
            _s.add_report(
                "BSS Logon Date: Sending at Time",
                ocg[0][2] == _send_time,
                ocg[0][2],
                _send_time,
                ""
            )

        # ==== Last Dayend Completed Date is last market date ====================
        _ldc = self.findstr(
            r'<tr><td>Last Dayend Completed.*?</td><td>(\d+) (\w+)</td>', mail.get_html(),
            _s, "Daily OCG Summary: Last Dayend Completed - 数据匹配"
        )
        if _ldc:
            _s.add_report(
                "Daily OCG Summary: Last Dayend Completed",
                bool(_ldc and _ldc[0][0] == self.trade_date.last_date_hk.strftime('%Y%m%d') and _ldc[0][1] == "Yes"),
                _ldc[0],
                f"{self.trade_date.last_date_hk.strftime('%Y%m%d')} Yes"
            )

        # ====== Coming Logon Date is current trading date ========================
        _cld = self.findstr(r'<tr><td>Coming Logon Date</td><td>(\d+)</td>', mail.get_html(),
                            _s, "Daily OCG Summary: Coming Logon Date"
                            )
        if _cld:
            _s.add_report(
                "Daily OCG Summary: Coming Logon Date",
                bool(_cld and _cld[0].strip() == self.trade_date.current.strftime('%Y%m%d')),
                _cld[0],
                self.trade_date.current.strftime('%Y%m%d')
            )
        # ====== Check statuses in OCG Summary ================
        for item in (
                "Front Vs OCG Push ID Matched ",
                "Front DB No. of Orders ",
                "OCGTL DB No. of Orders",
        ):
            _gs = self.findstr(
                r"<tr><td>(%s)</td><td>(\w+)</td><td>(\d+)</td><td>(\d+)</td><td>(\d+)</td></tr>" % item,
                mail.get_html(),
                _s, f"{item} 数据匹配"
            )
            if _gs:
                _gs = _gs[0]
                _s.add_report(
                    f"Check statuses in OCG Summary: {item}",
                    _gs[4] == "0",
                    _gs, "Difference[col 5] = 0"
                )

        # ===== Trading status in OCG Summary =======================
        for mk, cg, stat in self.findstr(
                r'<td>(HKG)</td><td>(\w*?)\W*?</td><td>(\w{2})</td></tr>', mail.get_html(),
                _s, "HKG Market Status 完整性验证", 4
        ):
            logger.debug(f"HKG and CSC Market Status 匹配到行： {mk} {cg} {stat}")
            # if cg in ('ETS', 'GEM', 'MAIN', 'NASD'):
            _s.add_report(
                f"HKG and CSC Market Status (Market = {cg})",
                stat == 'NO', stat, "NO"
            )

        # ===== Have record for DataFeed Record except IndexData =====
        for mk, record in self.findstr(
                r'<tr><td>(HKG|SHA|SZA|188.*?|81.*?)</td><td>(\d+)</td></tr>', mail.get_html(),
                _s, "No of DataFeed Record: 数据匹配完整性", 15
        ):
            logger.debug(f"No of DataFeed Record 匹配到行： {mk=} {record=}")
            if mk in ('188 IndexData', "81 IndexData"):
                _s.add_report(
                    f"No of DataFeed Record: ({mk})",
                    record == "0",
                    record, "0"
                )
            else:
                _s.add_report(
                    f"No of DataFeed Record: ({mk})",
                    int(record) > 0,
                    record, "> 0"
                )
        return _s

    def check_1_21_daily_instrument_changed(self) -> Step:
        _s = Step(1, 21, "0836 Daily Instrument Changed (email received)")
        self.get_mail(
            "Daily Instrument Changed",
            self.trade_date.current.strftime('%Y-%m-%d 08:35'),
            self.trade_date.current.strftime('%Y-%m-%d 08:37'),
            _s
        )
        return _s

    def check_2_2_0901_daily_pushlog_order_status(self) -> Step:
        _s = Step(2, 2, "09:01 PushLog email - Order Status Checking")
        logger.info(_s)
        mail = self.get_mail(
            "Daily PushLog Checking",
            self.trade_date.current.strftime('%Y-%m-%d 09:00'),
            self.trade_date.current.strftime('%Y-%m-%d 09:02'),
            _s
        )
        # ===== BSS Logon sending at time is updated to T09:01
        _gs = self.findstr(
            r'<td>(OCG Dealer)</td><td>(\d{8})</td><td>(.{19}).*?</td>', mail.get_html(),
            _s, "BSS Logon sending at time - 数据匹配"
        )
        if _gs:
            _s.add_report(
                "BSS Logon sending at time is updated to T09:01:00",
                _gs[0][2] == self.trade_date.current.strftime('%Y-%m-%dT09:01:00'),
                _gs[0], self.trade_date.current.strftime('%Y-%m-%dT09:01:00')
            )

        # ===== Statuses of HKG market ETS/GEM/MAIN/NASD are updated to 'OI' ======
        for mk, cg, stat in self.findstr(
                r'<td>(HKG)</td><td>(\w*?)\W*?</td><td>(\w{2})</td></tr>', mail.get_html(),
                _s, "HKG Market Status 完整性验证", 4
        ):
            logger.debug(f"HKG and CSC Market Status 匹配到行： {mk} {cg} {stat}")
            # if cg in ('ETS', 'GEM', 'MAIN', 'NASD'):
            _s.add_report(
                f"HKG and CSC Market Status (Market = {cg})",
                stat == 'OI', stat, "OI"
            )

        # ===== Have record for DataFeed Record except IndexData =====
        for mk, record in self.findstr(
                r'<tr><td>(HKG|SHA|SZA|188.*?|81.*?)</td><td>(\d+)</td></tr>', mail.get_html(),
                _s, "No of DataFeed Record: 数据匹配完整性", 15
        ):
            logger.debug(f"No of DataFeed Record 匹配到行： {mk=} {record=}")
            _s.add_report(
                f"No of DataFeed Record: ({mk})",
                int(record) > 0,
                record, "> 0"
            )

        # ===== HKG order speech < 0.01 sec and status is updated to 'QUEUED' or 'DEL' ======
        _gs = self.findstr(
            # <th>PSEQNO</th><tr><td>0</td><td>0</td><td>&#x20;</td><td>1900-01-01T00:00:00</td><td>1900-01-01T00:00:00</td><td>0</td><td>0</td></tr>
            r'<th>PSEQNO</th><tr><td>(\d+)</td><td>(\w+)</td><td>(.*?)</td><td>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})</td><td>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})</td><td>(\d+)</td><td>(\d+)</td></tr>',
            mail.get_html(),
            _s, "Daily HKG Orders Speed Check - 数据匹配完整性",
        )
        if _gs:
            _gs = _gs[0]
            _p_str = ''
            try:
                _p_str = html.unescape(_gs[2]).replace(" ", "")
                _p_sec = float(_p_str)
            except ValueError:
                _p_sec = 0
            _s.add_report(
                "HKG order speech < 0.01 sec",
                _p_sec < 0.01,
                _p_str, "< 0.01",
                "邮件中可能无有效数据"
            )
            _s.add_report(
                "HKG order status is updated to 'QUEUED' or 'DEL'",
                _gs[1] in ["QUEUED", "DEL", "0"],
                _gs[1], 'in ["QUEUED", "DEL", "0"]',
                '邮件中可能无有效数据'
            )

        return _s

    def check_3_2_kstar_quotes_started(self) -> Step:
        _s = Step(3, 2, "金士达：上海行情，深圳行情采集启动状态")
        mail = self.get_mail(
            # 金仕达V8异常交易系统[2026073009:15:02 ]运行日报
            f"金仕达V8异常交易系统[{self.trade_date.current.strftime('%Y%m%d09:15')}",
            self.trade_date.current.strftime('%Y-%m-%d 09:14'),
            self.trade_date.current.strftime('%Y-%m-%d 09:17'),
            _s
        )
        m_text = mail.get_html()  # .encode().decode(encoding="GBK")

        for s in ("上海行情", "深圳行情"):
            # _d, _, hq, status
            _gs = self.findstr(f"<tr.*?><td.*?>({self.trade_date.current.strftime('%Y%m%d')})</td>"
                               f"<td.*?>(行情采集)</td><td.*?>({s})</td><td.*?>(.*?)</td></tr>", m_text,
                               _s, "行情采集 数据匹配", 1
                               )
            if _gs:
                _s.add_report(
                    f"「{s}」",
                    _gs[0][3] == "启动成功",
                    _gs[0], "启动成功"
                )
        return _s

    def check_3_3_exec_job_status(self) -> Step:
        _s = Step(3, 3, "金士达：任务执行状态")
        mail = self.get_mail(
            # 金仕达V8异常交易系统[2026073009:15:02 ]运行日报
            f"金仕达V8异常交易系统[{self.trade_date.current.strftime('%Y%m%d09:15')}",
            self.trade_date.current.strftime('%Y-%m-%d 09:14'),
            self.trade_date.current.strftime('%Y-%m-%d 09:17'),
            _s
        )
        _gs = self.findstr(f"<tr.*?><td.*?>({self.trade_date.last_date_cn.strftime('%Y%m%d')})</td>"
                           f"<td.*?>(实时数据处理|盘后数据采集)</td><td.*?>(.*?)</td><td.*?>(.*?)</td></tr>",
                           mail.get_html(),
                           _s, "任务执行 数据匹配", 17
                           )
        if _gs:
            for __ in _gs:
                _s.add_report(__[2], __[3] == "成功", __, "成功")

        return _s

    def check_3_4_trade_data_capture(self) -> Step:
        _s = Step(3, 4, "金士达：交易数据采集状态Trade Data Capture")
        mail = self.get_mail(
            # 金仕达V8异常交易系统[2026073009:15:02 ]运行日报
            f"金仕达V8异常交易系统[{self.trade_date.current.strftime('%Y%m%d09:15')}",
            self.trade_date.current.strftime('%Y-%m-%d 09:14'),
            self.trade_date.current.strftime('%Y-%m-%d 09:17'),
            _s
        )
        for data in ("委托数据", "成交数据"):
            _gs = self.findstr(f"<tr.*?><td.*?>({self.trade_date.current.strftime('%Y%m%d')})</td>"
                               f"<td.*?>({data})</td><td.*?>(.*?)</td><td.*?>(.*?)</td></tr>", mail.get_html(),
                               _s, f"交易数据采集-「{data}」 数据匹配", 1
                               )
            if _gs:
                dd = _gs[0]
                _s.add_report(dd[1], dd[2] == "成功" or dd[3] == "0", dd, "成功 or 数量=0")

        return _s

    def main_all(self):
        _checks = [_ for _ in sorted(self.__dir__()) if _.startswith("check")]
        logger.info(f"已创建 {len(_checks)} 个测试： {_checks}")
        self._main(
            *[getattr(self, _) for _ in _checks],
        )


if __name__ == '__main__':
    import datetime
    from utils import load_env

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s",
    )

    load_env()
    _td = datetime.date(2026, 7, 30)
    _mc = MorningCheck(_td, cache_db=SCRIPT_DIR / "cache_morning_check.db")
    _mc.main_all()
    _mc.report()
    # _mc.check_1_14_tp1_fo_market_info()

    # _mc.report_to_mail()
