# 通用项目生命周期与命令

技能安装目录以下简称 SKILL；目标项目绝对路径以下简称 PROJECT。这些是文档占位符，不要把占位符写入实际配置。

## 初始化共同维护文件

先将用户完整目标、允许范围、完成标准写到一份脱敏目标文件，然后：

```sh
python3 "$SKILL/scripts/project.py" init --project "$PROJECT" --project-id "$PROJECT_ID" --goal-file "$GOAL_FILE"
```

已有 PM 时加 `--chat-url https://chatgpt.com/c/真实会话ID`。这只绑定地址，不代表沟通已验证。重复相同 init 幂等；不同目标/项目 ID 拒绝覆盖。已有 .gpt-pm/rounds 历史可以保留。共同文件：

| 文件 | 维护方式 |
|---|---|
| PROJECT.json | 脚本维护项目 ID、固定会话、阶段、审核门槛与当前轮次 |
| GOAL.md | 用户目标、范围和最终完成条件；目标变化须明确记录来源 |
| PLAN.md | 本地 accept 后从网页下一步文档同步；不假设固定里程碑数量 |
| ACCEPTANCE.md | 当前阶段的可执行验收 |
| STATUS.md | 当前阶段、状态、待审轮次、最近已接收轮次 |
| DECISIONS.md | 追加阶段/审核决策，重要架构变化另由本地简述来源 |
| PM_INSTRUCTIONS.md | init 从独立技能复制的最小网页 PM 指令 |

项目内文件被 WebCodex 访问，网页不需要访问 ~/.codex。全局技能不保存任何项目配置。其他模型可直接读取 SKILL.md 使用，无需安装到 ChatGPT 插件。

MANAGER_CONFIG.json 保存 requested/observed 配置，纳入审核指纹。首次准备审核前，按 [authority.md](authority.md) 的 configure 命令记录实际 UI；默认 strict 尚未核实时 prepare 审核会拒绝；consult 可诊断；用户已授权 keep_existing 时按策略沿用当前会话。

## 启动会话与握手

本地浏览器 `chrome_chat.py new` 创建项目专用标签；读取页面确认 Chat/Work 与模型，不改变用户偏好。已有 URL 使用 list 查找对应标签，不开重复会话。还没有标签时在新标签打开准确已绑定 URL。

```sh
python3 "$SKILL/scripts/project.py" prepare --project "$PROJECT" --kind bootstrap --summary "$REPORT" --files README.md src tests
```

显式选择实际存在的相关文件。首次空项目可选择用户新建的目标说明文件；不传整个主目录。生成 PROMPT.txt 和 nonce；用 chrome_chat.py send 发送一次，随后读取真实 URL：

```sh
python3 "$SKILL/scripts/chrome_chat.py" send --tab "$TAB_ID" --prompt "$ROUND/PROMPT.txt" --receipt "$ROUND/browser-receipt.json"
python3 "$SKILL/scripts/project.py" bind --project "$PROJECT" --chat-url "$CHAT_URL"
python3 "$SKILL/scripts/project.py" accept --project "$PROJECT"
```

首次握手只有完整 outbox、正确 nonce、未变更源码与共同控制文件、approved 才会设置 bootstrapApproved=true。不能手改 PROJECT.json 伪造。

## 目标模式的每阶段循环

```sh
python3 "$SKILL/scripts/project.py" begin --project "$PROJECT"
# 按 PLAN 和 ACCEPTANCE 实施、验证、审查；生成本轮报告
python3 "$SKILL/scripts/project.py" prepare --project "$PROJECT" --kind stage --summary "$REPORT" --files src tests README.md
python3 "$SKILL/scripts/chrome_chat.py" send --tab "$TAB_ID" --expected-url "$CHAT_URL" --prompt "$ROUND/PROMPT.txt" --receipt "$ROUND/browser-receipt.json"
# 等待 PM 完成；不要边审边改。默认 chat：抓取真实回复后再 accept
python3 "$SKILL/scripts/chat_review.py" --tab "$TAB_ID" --round "$ROUND"
python3 "$SKILL/scripts/project.py" accept --project "$PROJECT"
```

accepted/verified 不等于 approved。读取 JSON 状态；approved 才推进下一阶段，changes_requested 是同阶段修正，blocked 停在依赖处。脚本可以返回完整 blocked 文档而不放行开发。

宿主目标循环应包含：实施 → 验证 → 阶段审核 → 接收纠偏 → 下一阶段。不要把“已发送 PM 消息”当成一个目标完成。默认仅阶段末沟通一次；阻塞或目标冲突才额外沟通。等待使用工具休眠或宿主事件能力，不高频模型推理轮询；没有等待能力就诚实留下 awaiting_review 供恢复。

## 完成与恢复

```sh
python3 "$SKILL/scripts/project.py" prepare --project "$PROJECT" --kind final --summary "$FINAL_REPORT" --files src tests README.md
# 同一 PM 会话发送；默认 chat，完整回复后先用 chat_review.py 抓取再 accept
python3 "$SKILL/scripts/project.py" accept --project "$PROJECT"
python3 "$SKILL/scripts/project.py" status --project "$PROJECT"
```

final 必须 approved 且 DONE.goalComplete=true，但仅进入 supervisor_review_pending。主管独立验证并执行 supervisor_review 后进入 owner_acceptance_pending；用户明确确认后由主管记录原文并执行 owner_confirm 才标 complete。开发者不得运行这两个角色专用命令。

已有 activeRound 时拒绝创建第二轮；先检查原会话是否在运行、发送是否成功、outbox 是否完整。发送不确定时 read 回查，禁止删除 receipt 重发。平台拒绝时：

```sh
python3 "$SKILL/scripts/project.py" blocked --project "$PROJECT" --reason "具体拒绝动作及平台原文"
```

此命令保留 activeRound，不会自动重试或放行。源码 stale 时若 PM 已返回完整 blocked，可 accept 存档后准备新轮；若输出不齐、平台拒绝或仍运行，保持阻塞，先解决真实外部条件。没有后台定时或服务。

## 单一维护者约束

同项目只有一个本地阶段协调者维护 PROJECT/PLAN/STATUS。其他本地模型可以做分配的开发，但阶段提交由协调者统一冻结、取快照；不要让两个模型同时 prepare/accept。不同项目可以独立执行，目录、round-id、URL 分别隔离。


## v3 初始化扩展与角色交付

init 还创建 CHARTER、ARCHITECTURE、MILESTONES、PROGRESS、ESCALATIONS、FINAL_REPORT、DEVELOPER_CONTRACT 以及 reports/、evidence/、supervisor/、owner/。主管必须把章程、架构和里程碑按实际项目补齐，不能将模板当已完成规划。阶段报告模板是 reports/STAGE_REPORT_TEMPLATE.md。

bootstrap 通过后生成可转发提示词：

```sh
python3 "$SKILL/scripts/project.py" developer_prompt --project "$PROJECT"
```

返回固定经理 URL 与项目特定 DEVELOPER_PROMPT.md。未通过 bootstrap 或项目 blocked/escalated 时拒绝签发开发提示词。

主管独立终验（或处理 escalated）：

```sh
python3 "$SKILL/scripts/project.py" supervisor_review --project "$PROJECT" --report "$REAL_SUPERVISOR_REPORT" --decision approved
```

终验批准前重新核对最终源码与目标/架构；拒绝可用 changes_requested，返回返工。升级问题 approved 表示主管已给出决策，状态仍回到 changes_requested 以落实纠偏，不代表总体通过。

只有主人明确确认后执行：

```sh
python3 "$SKILL/scripts/project.py" owner_confirm --project "$PROJECT" --confirmation "$ACTUAL_OWNER_MESSAGE_RECORD"
```

记录真实回复及来源/时间，不用模板伪造。脚本验证主管报告未变、源码与共同文件未变，然后标 complete。角色权限属于协作规范，不是操作系统隔离。

旧 v2/v3 使用 recovery.md 中的 cancel_unsent/migrate 命令，禁止手改状态；迁移后重新 bootstrap。

两段提示词交付命令及顺序见 usage.md；consult 诊断和 keep_existing 用户授权配置见 authority.md。
