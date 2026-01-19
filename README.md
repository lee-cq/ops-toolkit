# 翻译工具包

实现一个翻译APP，只需要英语，简体中文，繁体中文，主要功能如下：
1. 基础翻译API(已经完成：config.api.translate_text)
2. 全局快捷键绑定：按下快捷键读取剪切板内容，并调用翻译API
3. 翻译结果对照到浮动窗口：将翻译API返回的结果放入浮动窗口中，焦点置于浮动窗口，允许按下esc关闭。
4. 后台托盘运行：启动后台托盘，使程序在后台允许，右键弹出菜单：翻译记录，运行日志，设置，退出
5. 翻译结果记录：将每次翻译的结果都收集到文件中，格式待定
6. 翻译日志记录：配置logging记录全部日志
7. 翻译结果分析：读取翻译结果文件，分析高频词汇并创建单词表
8. 记录、和分析结果导出：允许将翻译结果导出为csv(time, src, dst)和分析的单词表(txt, 一行一个单词)

## CHANGELOG

### 1.5
1. 新增teams通知监控
2. 变更CHANGELOG位置到README.md
3. 更新依赖
4. trams监控添加了配置项

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
8. config.py Config.Feishu 添加空默认值，确认无配置启动

### 1.1
1. 添加ROW REQUEST日志方便分析Translate API的原始记录
2. 防止调整translate窗口时的无限递归
3. 更新版本号生成机制
4. api_abs 中添加Response使用字符串提示类型
5. 优化自动识别语言逻辑，移除tw因为基本用不到，现在繁体在识别和翻译前将直接转换为简体 #20 #22
6. 因开发者不再维护zhconv，将zhconv内联到项目中，自维护，基于1.4.4版本

### 1.0.0
