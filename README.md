# OPS工具包

## 安装

### 1. 环境要求:

`Python 3.13+`

### 2. 安装:

1. 从Git源码安装(最新版本)：`pip install git+https://cnb.cool/leecq/ops-toolkit.git`
2. 从制品库安装(稳定版本)：`pip install ops-toolkit -i https://pypi.cnb.cool/leecq/pytools/-/packages/simple`

### 3. 使用说明:

1. 安装程序将会创建2个exe，位于Python安装目录的Scripts文件夹下：
   - `ops-toolkit.exe`：GUI主程序，将会在单独的进程中启动
   - `ops-toolkit-cli.exe`：带调试日志的GUI程序，会在控制台输出调试日志
2. 翻译功能需要添加百度翻译API密钥，并开通“大模型文本翻译API” [官网](https://fanyi-api.baidu.com/)


## 主要功能：

1. 翻译
2. keep live
3. 阿里云SLS日志切割工具
4. Teams消息监控通知工具

## 1. APP框架
1. 后台托盘运行：启动后台托盘，使程序在后台允许，右键弹出菜单：翻译记录，运行日志，设置，退出等

## 2. 翻译模块

1. 通过监听快捷键，快速将剪切板的内容通过百度或腾讯的翻译API获取翻译内容；
2. 翻译结果的中英文对照结果在当前鼠标位置创建浮动窗口并显示翻译结果；
3. 焦点置于浮动窗口，允许按下esc关闭，双击窗口将翻译结果复制到剪切板；
4. 翻译结果记录：将每次翻译的结果都收集到文件中作为缓存；
5. 每次翻译时会检查缓存中是否有该内容的翻译结果，如果有则直接显示，否则调用翻译API获取翻译结果并显示；
6. 记录、和分析结果导出：允许将翻译结果导出为csv(time, src, dst)。

## 3. Keepalive 保持电脑活跃

监听检查周期内是否有键盘或鼠标活动，如果没有将向操作系统发送Ctrl键；

## 阿里云SLS日志切割工具

1. 在阿里云SLS平台获取JSON导出的链接，程序将自动下载并分割为原始日志文件。
2. 程序监听剪切板，自动识别阿里云SLS链接，并弹出窗口下载窗口。
3. TODO: SLS导出时受限于100W行的限制，将使用Aliyun SDK 来下载大于100W行的日志。

## 4. Teams消息监控通知工具

1. 截图监听Teams的托盘区域，消息区域，活动区域和团队区域，如果有红色，则判断为收到信息，触发通知
2. 如果触发通知：调用系统通知接口，持续通知用户，直到用户点击通知关闭
3. 需要手动确认图标区域；
4. 开启监听时，系统会自动开启keepalive功能，保持电脑活跃
5. 开启监听时，系统会提示用户跳大系统音量，防止错过通知


## CHANGELOG

### 1.6
1. 移除飞书相关代码
2. 重构项目文件结构
3. 添加cnb CI配置
4. 优化通知提示，添加app_id
5. 优化坐标选择器，先截图在创建窗口，避免在创建窗口后内容变更，保证获得的坐标准确
6. 优化坐标选择器，选择完成后先清空原来的内容
7. 修复开机自启配置错误

### 1.5
1. 新增teams通知监控
2. 变更CHANGELOG位置到README.md
3. 更新依赖
4. trams监控添加了配置项
5. trams监控添加了GUI日志
6. 完善README.md，添加使用说明

### 1.4
1. 新增aliyun_sls_split.py，用于切割阿里云日志下载文件
2. 新增UI到托盘，打开下载窗口
3. 新增自动识别aliyun SLS链接，自动弹出窗口
4. 优化Hostname的处理，移除域名
5. 单一文件中添加source, path, content三列，用|||分隔
6. 优化ui_window_sls_split.py，打开工作目录选择默认值

### 1.3
1. 更改baidu翻译API接口为aiTextTranslate
2. 新增clipboard_monitor.py，用于监听剪切板内容变化
3. 新增clipboard窗口，用于展示剪切板内容
4. 新增开机自启配置项
5. 修复开机自启配置错误的程序路径

### 1.2
1. 添加translate-cli
2. 添加other_tools.keepalive.py，用于保持电脑活跃
3. 添加other_tools.hourly_reminder.py，用于每小时提醒
4. fix: zhconv导入失败
5. fix: json依赖未被包含
6. 优化:pytray MENU 的更新逻辑
7. hourly_reminder支持在最长4小时后开始提醒

### 1.1
1. 添加ROW REQUEST日志方便分析Translate API的原始记录
2. 防止调整translate窗口时的无限递归
3. 更新版本号生成机制
4. api_abs 中添加Response使用字符串提示类型
5. 优化自动识别语言逻辑，移除tw因为基本用不到，现在繁体在识别和翻译前将直接转换为简体 #20 #22
6. 因开发者不再维护zhconv，将zhconv内联到项目中，自维护，基于1.4.4版本

### 1.0.0