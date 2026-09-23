# 首次配置：哪些人需要 WebCodex？

本地技术员可用 Codex、Claude Code 或其他本机模型/编辑器，不要求每个模型都安装 WebCodex。网页 GPT 要独立读本机文件和运行检查，需要项目机器上的 WebCodex Runtime，以及该 GPT 账号已连接的 MCP 插件。安装本技能不会自动安装或授权 WebCodex。

## 官方入口（2026-09-23 核验；界面变化以原项目为准）

- [WebCodex 原项目，作者 yyjeqhc 及贡献者](https://github.com/yyjeqhc/webcodex)
- [下载 Releases](https://github.com/yyjeqhc/webcodex/releases)
- [桌面安装与 ChatGPT 连接](https://github.com/yyjeqhc/webcodex/blob/main/docs/desktop-install.md)
- [完整配置：CLI / Linux / 已有 Server](https://github.com/yyjeqhc/webcodex/blob/main/docs/PERSONAL_SETUP.md)
- [MCP 文档](https://github.com/yyjeqhc/webcodex/blob/main/docs/MCP.md)
- [故障排查](https://github.com/yyjeqhc/webcodex/blob/main/docs/TROUBLESHOOTING.md)

## 朋友首次使用

1. 安装 Python 3.11 或更高版本以及本技能。先运行 `python3 scripts/doctor.py`，只检查本机依赖，不读取配置密钥，也不声称连接已通。
2. macOS/Windows 用户按官方桌面指南安装对应版本，选择真实项目目录，确认 Runtime 中 Service、Runner、Project 就绪。Linux 或已有服务器按官方完整配置。
3. 按官方指南配置 ChatGPT 到 Server 的连接。普通网页无法直接访问你电脑的 localhost；需要官方支持的可达连接。Tunnel 配对、账号登录、密钥设置由用户在官方界面完成；不要把密钥发给模型或提交 Git。
4. 在 GPT 网页连接 WebCodex 插件，实际列出刚选项目的顶层文件。这个项目读取才是通路证据；不要只看本机绿色状态。
5. Codex 主管解析真实项目 ID，初始化 `.gpt-pm/`，建立固定网页经理，并做 nonce 文件创建+本地读回测试。完整 bootstrap 审核通过后交给技术员。

本技能和 WebCodex 是独立项目，不打包 WebCodex 二进制/源代码，不承诺免额度。ChatGPT 账号是否有相应功能取决于实际账户与当前产品权限；没有连接能力时报告缺少的环节。

## 浏览器控制

附带 `chrome_chat.py` 支持 macOS Google Chrome，使用用户实际登录的可见标签；`ego_chat.py` 支持已有 Ego Lite task space 中受管的 ChatGPT 页面。两者都不读取 Cookie、不调用 ChatGPT 私有 API。Chrome 需用户允许来自 Apple 事件的 JavaScript；Ego 与 Chrome 的登录会话隔离。登录和系统授权由用户完成。Windows/Linux 需在当地实测可用通道，不能把 macOS 验证推广到其他系统。

没有浏览器控制时可手工发送生成的 PROMPT.txt，但这是人工辅助模式；不能称全自动。正式目标循环必须先验证所选实际通信方式。
