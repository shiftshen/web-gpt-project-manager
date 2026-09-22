# 网页问答与本地留证

## 默认方式

- 首次 bootstrap：真实文件探针，网页写当前 outbox，校验连接；已经有效的握手不重复。
- 日常咨询：在固定网页直接短问短答，不要求经理写文件。非阶段决定可由开发者如实记入 DIALOGUE.md（时间、URL、问题、原文、采取动作）。普通答复不能冒充阶段批准。
- 阶段/replan/final：默认 `transport=chat`。经理按简短摘要给结论、下一步及验收，以一个小 JSON 代码块表达；本地抓取真实网页原文、验证当前轮次和源码，再 accept。本地保存不是“经理通过 WebCodex 写文件”。
- 特殊需要经理写文件才显式 `--transport files`。不能要求经理默认写四份文件或运行测试。

## 命令

```sh
python3 "$SKILL/scripts/project.py" prepare --project "$PROJECT" --kind stage --summary "$REPORT" --files src tests review-evidence
# --transport 默认 chat（bootstrap 默认 files）；用原会话发送 PROMPT.txt
python3 "$SKILL/scripts/chrome_chat.py" send --tab "$TAB_ID" --expected-url "$CHAT_URL" --prompt "$ROUND/PROMPT.txt" --receipt "$ROUND/browser-receipt.json"
# 等待本轮完整回复后，抓取实际可见消息，不手工创造经理回复
python3 "$SKILL/scripts/chat_review.py" --tab "$TAB_ID" --round "$ROUND"
python3 "$SKILL/scripts/project.py" accept --project "$PROJECT"
```

经理输出只需 roundId、status、reason、nextTask、acceptance；final 再加 goalComplete。字段说明在自动生成的简短提示词里。无需经理计算源码哈希，冻结和哈希核对由本地完成。

CHAT_REPLY.json 保存实际 Chrome 会话 URL、时间、用户原消息与经理原回复；CHAT_ACCEPTED.json 保存接收时哈希。PLAN/ACCEPTANCE 是本地从真实结论同步，不创建假的 WebCodex outbox/DONE。该记录用于可追溯协作，不是密码学身份证明。

## 重要追问和必要打断

经理遗漏关键条件、理解错目标、开始无关研究或代码研发时，可马上纠偏。先说明当前场景/进度和一个具体问题，必要时停止当前生成后问；不因回复慢、缺少耐心或想催促就打断。

同轮追问附 `FOLLOWUP_FOR: 原 roundId`，冻结范围不变。经理最终结论仍引用原 roundId；只接收最后完整且明确的回复。保留中间对话，不能将被打断的半句当批准。发送结果未知先核对，不重复原任务。普通澄清不重新创建整个目标。

chrome_chat.py send 只负责首次有 roundId 的防重复提交，故保留忙碌拦截；重要追问/打断使用宿主已授权的浏览器交互完成，不删除 receipt 绕过 send 的保护。操作前核对 URL、当前轮次和停生成按钮；用户接管即停止。

缺明确状态/roundId 时问一句补充确认，不让经理重做研究。CHAT_REPLY 已保存后若还需改结论，保留旧轮，使用恢复机制新轮，不能覆盖既有证据。源文件变化则新快照，不把旧答案移用新代码。
