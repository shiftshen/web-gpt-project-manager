# 浏览器桥接

## Ego Lite 与 DSH Web

当开发者在 DSH Web 工作、网页经理使用已登录的 Ego Lite ChatGPT 标签时，复用同一个 task space，记录 `spaceId` 与已管理的 ChatGPT `page` 标签。不要新建空间恢复失败页面。`ego_chat.py` 只操作该页面，不读取 Cookie 或 ChatGPT 私有 API；Ego 与用户 Chrome 相互隔离。用户接管空间后停止自动操作。

```sh
python3 scripts/ego_chat.py read --space SPACE_ID --page PAGE_LABEL
python3 scripts/ego_chat.py send --space SPACE_ID --page PAGE_LABEL --prompt /绝对路径/PROMPT.txt --receipt /绝对路径/browser-receipt.json --expected-url https://chatgpt.com/c/真实会话ID
python3 scripts/chat_review.py --browser ego --space SPACE_ID --page PAGE_LABEL --round /绝对路径/rounds/轮次
```

首次 bootstrap 的 `send` 不传 `--expected-url`，发送后读回真实会话 URL 并用 `project.py bind`。发送结果不确定时检查页面，不删除 receipt 重发。阶段审核抓取可见 Ego 原文并记录 `visible-ego-transcript` 来源；bootstrap 仍须网页经理通过 WebCodex 写回真实 nonce 和完整 outbox。Ego 登录不等于 WebCodex 已连接。

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

## 防止后台标签/旧面板导致残缺读取

先 list 确认窗口、tab ID 与 URL，可用 `chrome_chat.py focus --tab TAB_ID` 将精确 ChatGPT 标签显示在用户 Chrome 中。若只读到“确认：”等片段，先检查是否仍生成、标签是否可见、旧工具详情面板是否遮挡；确认为旧面板时可关闭后读回，不发送催促或要求经理重做研究。不能据残缺 DOM 断言真实回复只有半句。用户接管后不再自动操作。

Composer text mismatch 是发送前草稿校验失败，不自动等于已发送。脚本现在有限等待编辑器稳定，仍保留内容校验。若已停在草稿：保留旧回执，核对准确会话无该轮用户消息、经理空闲、草稿与原文一致、快照仍新鲜后，才可完成该草稿的一次发送并另记恢复回执。未知发送结果或内容真有差异不得盲目重发。
