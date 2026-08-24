# MorningCheck 早盘自动化检查工具使用文档
## 一、工具概述  
MorningCheck 是一款适配港股、A股交易场景的早盘自动化巡检 Python 工具，用于替代人工早班巡检工作。工具通过 IMAP 协议抓取业务监控邮件，解析 HTML 邮件正文、DOCX 附件，正则校验各类交易系统运行状态，自动生成结构化报告，支持日志输出、邮件推送、Teams 消息推送，适配交易日自动校验规则。
覆盖巡检业务：易盛北斗星托管系统、AML/SAS 风控系统、TP1 网关/MDS/MQ 服务、OCG 前端交易系统、金仕达 V8 交易系统等核心早盘巡检场景。


## 二、核心功能
- IMAP 邮件搜索与拉取，
- 解析 HTML 邮件、解压解析 DOCX 附件，提取文本数据
- 内置交易日、节假日判断，自动区分 A 股、港股休市规则
- 正则校验系统运行状态、交易数据、服务连接状态
- 自动生成 JSON 结构化报告、HTML 可视化报告
- 支持日志记录、邮件报告推送、Teams 企业微信推送
- 异常捕获容错，单项检查失败不中断整体巡检流程

## 三、项目整体结构  
```
项目根目录/
├── morning_check.py                      # 主程序脚本
├── __main__.py                           # CLI 入口
├── deps/                                # 依赖模块目录
│   ├── docx2txt.py                   
│   └── html2text.py
├── mail_manager.py                  # IMAP 邮件管理模块
├── utils.py                         # 全局工具函数、路径配置
├── notification.py                  # Teams 消息推送模块
├── .env                                 # 环境变量配置文件（核心配置）
├── holiday_xxxx.json                    # 年度节假日配置文件（必填）
├── template_report_morning_check.html   # 报告 HTML 模板
├── reports/                             # 巡检报告输出目录（自动生成）
│   ├── morning_check_日期.json
│   └── morning_check_日期.html
└── logs/                                # 日志
   └── morning-check/
        └── check-date.log              

```
### 3.1 必备文件说明
- holiday_xxxx.json：年度节假日配置文件，区分 A 股、港股休市日期，程序依赖该文件判断交易日，格式如下：
{
  "cn": ["2026-01-01", "2026-05-01"],
  "hk": ["2026-04-05", "2026-10-01"]
}
- .env：环境变量配置文件，存放邮箱、推送地址等隐私配置
- template_report_morning_check.html：前端可视化报告模板，不可缺失
## 四、环境配置
### 4.1 环境变量配置（.env）
所有配置项必须正确填写，否则邮件拉取、消息推送功能失效。
```dotenv
# MailManager - IMAP
IMAP_HOST=
IMAP_PORT=25
IMAP_USERNAME=
IMAP_PASSWORD=
IMAP_SSL=

# MailManger - SMTP
SMTP_HOST=
SMTP_PORT=465
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_SSL=

# Teams Notification
TEAMS_WEBHOOK_URL=

# 邮件所在目录，ALL将遍历全部的目录
MORNING_CHECK_FOLDER=ALL
# 邮件报告发送信息
MORNING_CHECK_MAIL_TO=
MORNING_CHECK_MAIL_CC=
# Teams 报告URL
MORNING_CHECK_TEAMS_WEBHOOK=
```

### 4.2 运行依赖
基于 Python3 运行，无需额外第三方库，仅依赖项目内置 deps 模块，原生库即可运行。  
## 五、核心模块详解
### 5.1 TradeDate 交易日模块
核心工具类，自动读取年度节假日文件，判断当日是否为交易日、自动计算上一交易日。
核心属性：
- current：当前巡检日期
- is_holiday_cn：A 股是否休市
- is_holiday_hk：港股是否休市
- last_date_cn：A 股上一交易日
- last_date_hk：港股上一交易日
### 5.2 Docx2Text 文档解析模块
纯原生实现 DOCX 文档解析，无需 python-docx 第三方库，内存解压读取 XML 节点，精准提取文档文字、制表符、换行符，适配邮件附件报表解析场景。
### 5.3 CheckStatus / Step 报告模块
- CheckStatus：最小检查单元，记录单条校验的状态、实际值、期望值、备注信息
- Step：单个巡检步骤，聚合多条检查项，自动统计成功/失败状态，自动持久化 JSON 报告
### 5.4 MorningCheck 主业务模块
程序入口核心类，集成所有巡检逻辑、邮件拉取、数据校验、报告生成、消息推送能力。
核心批量执行方法（适配分时定时任务）：
- main_0800()：08:00 批次巡检
- main_0818()：08:18 批次巡检
- main_0836()：08:36 批次巡检
- main_0901()：09:01 批次巡检
- main_0916()：09:16 批次巡检
- main_all()：执行全部巡检用例（全量测试使用）
### 5.5 MailManager 邮件管理类
通过拉取，下载，缓存等核心功能。
```python
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
        **kwargs,
) -> Iterator[Mail]:
    """从缓存数据库中查询邮件，如果没找到去imap中缓存后再找

    :param subject: 邮件标题
    :param time_start: 搜索的起始时间
    :param time_end: 搜索的结束时间
    :param folder: 检索的目录 - 仅缓存邮件使用，默认在数据库中全局搜索
    :param is_desc: 是否倒序
    :param where_sql: WEERE 查询的SQL原文，将原样拼接到查询后面，以OR AND 开头
    :param _recached:

    :return: Iterator[Mail] 返回Mail对象的生成器
    """
```
## 六、运行使用方法
### 6.1 从脚本运行
```python
if __name__ == '__main__':
    import datetime
    from utils import load_env

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s",
    )

    load_env()
    # 指定巡检日期
    _td = datetime.date(2026, 8, 24)
    _mc = MorningCheck(_td, cache_db=SCRIPT_DIR / "cache_morning_check.db")
    # 执行全部检查
    _mc.main_all()
    # 生成可视化报告
    _mc.report()
    # 可选：推送邮件、Teams消息
    # _mc.report_to_mail()
    # _mc.report_to_teams()
```

### 6.2 从CLI运行
```text
usage: python __main__.py morning-check [-h] [-t TODAY] [-r] [-e] [-m] times [times ...]

positional arguments:
  times              时间参数，可选：0800 0818 0836 0901 0915 all

options:
  -h, --help         show this help message and exit
  -t, --today TODAY  检查的日期
  -r, --report       生成报告
  -e, --email        发送报告到邮件
  -m, --teams        发送报告到teams
```


## 七、新增/修改巡检步骤指南
### 7.1 新增检查函数规范
1. 函数命名格式：check_分区_序号_业务名称
2. 必须返回Step 对象
3. 内部流程：初始化Step - 拉取邮件 - 数据解析 - 状态校验 - 写入报告
### 8.2 新增示例模板
```python
def check_2_05_new_service_check(self) -> Step:
    _s = Step(2, 5, "新增业务系统巡检")
    logger.info(f"Start Check: {_s}")
    # 拉取对应邮件
    mail = self.get_mail(
        subject="业务系统运行日报",
        time_start=self.trade_date.current.strftime("%Y-%m-%d 08:20"),
        time_end=self.trade_date.current.strftime("%Y-%m-%d 08:25"),
        step=_s
    )
    if not mail:
        return _s
    # 正则解析校验
    res = self.findstr(r"正则表达式", mail.get_html(), _s, "业务状态校验", 1)
    # 写入检查结果
    _s.add_report(
        name="业务运行状态",
        status=True,
        actual="正常",
        expected="正常",
        msg="自动化校验通过"
    )
    return _s
```
新增完成后，将函数加入对应时段的main_xxx() 方法即可生效。
## 八、核心工具方法说明
### 8.1 get_mail()
根据邮件主题、时间窗口搜索邮箱邮件，自动生成「邮件是否找到」检查项，返回邮件对象。
邮件对象可用方法：get_html()、get_attachment()、get_send_time()
### 8.2 findstr()
封装正则匹配工具，自动校验匹配数量，匹配不达标自动生成失败报告，简化正则校验逻辑。

## 九、常见问题排查
- 邮件查找失败：检查 IMAP 配置、邮件文件夹、时间窗口、邮件主题匹配规则，确认邮件已送达邮箱
- 正则匹配无数据：导出邮件 HTML 源码，核对正则表达式，适配邮件格式变更
- 节假日报错：检查对应年份 holiday_xxxx.json 文件是否存在、JSON 格式是否合法
- 报告生成失败：检查项目目录权限、HTML 模板文件是否缺失
- 推送失败：核对邮件收件人、Teams webhook 地址环境变量配置

