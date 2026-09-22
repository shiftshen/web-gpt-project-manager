# 浏览器桥接

macOS 已登录的 Google Chrome 是本机实测路径。使用脚本不读取 Cookie、不调用 ChatGPT 私有 API、不提取账号令牌。Windows/Linux 用宿主浏览器工具按相同协议执行，未声称已实测这些浏览器平台。

先运行 chrome_chat.py list，只列 ChatGPT 标签，使用返回的稳定 tabId；不要以“第一个窗口第几个标签”定位，用户切换窗口会改变顺序。

命令：
- python3 scripts/chrome_chat.py list
- python3 scripts/chrome_chat.py new
- python3 scripts/chrome_chat.py read --tab TAB_ID
- python3 scripts/chrome_chat.py send --tab TAB_ID --prompt /绝对路径/PROMPT.txt --receipt /绝对路径/browser-receipt.json

new 仅新建普通首页标签；发送前读取页面，确认账号、Chat/Work、模型和输入框，按用户选择。脚本不会自动切换模式或选择模型。若 WebCodex 需要 Work，记录实际 UI，不声称普通聊天完成工具执行。

send 会拒绝正在生成的页面、非空草稿、已经存在相同轮次、既有 receipt。提交前写 intent，提交后读回轮次与 URL。错误/超时留下 uncertain 意图；先 read 和核验本地 outbox，禁止删除 receipt 盲目重试。脚本使用 DOM 可见输入框和按钮；选择器变化时停止并检查页面，不能用猜测选择器无限点击。

若 Chrome 禁止 AppleScript JavaScript，需由用户在 Chrome “视图 → 开发者 → 允许来自 Apple 事件的 JavaScript”设置；不得通过修改隐私设置或换隔离浏览器冒充已登录 Chrome。用户接管后立即停止。Ego 仅在用户接受隔离会话且 Chrome 不可靠时使用，明确报告。

等待不等于持续调用模型。无需每分钟检查，也无需让网页 GPT 创建定时任务。单次核对完成就退出；任务尚在运行时留存 URL 和 round-id。

读取结果中的 headerText/configurationControls 有助于定位模型菜单，但只是 UI 文本，不自动判定当前模型。用户已授权浏览器协作时，打开/关闭菜单读取选中项不需要重复确认；不要选择模型或触发重生成。一次有边界诊断后仍读不到就保留 unknown，按配置策略继续/consult；不能根据跨调用读取失败断言产品禁止菜单交互。
