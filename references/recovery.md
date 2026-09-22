# 动态规划、问题处理与恢复

| 情况 | 下一动作 | 禁止事项 |
|---|---|---|
| 普通测试失败 | 本地定位根因、最小修复、相关回归 | 每个失败都问经理 |
| 方案不可实现/有更好替代 | 小范围证据验证，prepare --kind replan | 暗改用户目标或无限重构 |
| 相同问题两轮返工 | 升级主管，明确证据和替代路线 | 无界重试 |
| 网页仍运行 | 等待原会话，保存轮次 | 停止、插话、重复提交 |
| 输出不齐/网络中断 | 读回 URL 和文件，诊断实际执行状态 | 删除 receipt 盲目重发 |
| 源码 stale | 停止并发写，PM blocked 后新快照 | 接受旧 approved |
| 原轮无法恢复 | 经理已停止且有解决条件证据后 recover | 伪造输出或审批 |
| 经理会话无法恢复 | 主管保留历史、replace_manager、重新 bootstrap | 静默换 URL |
| 安全/审批拒绝 | 记录原文，等待真实授权/条件变化 | 改写/分批/换工具绕过 |
| 上下文耗尽/换执行模型 | 读持久状态恢复目标和当前轮次 | 重新创建重复项目 |

正常阶段重规划：
`python3 scripts/project.py prepare --project PROJECT --kind replan --summary REPORT --files src tests`
批准后更新计划版本；stage 只表示进度序号，不代表固定技术路线。

对于无法恢复的 pending/blocked 轮，先确认网页经理已经停止、没有正在执行的写入，记录诊断、真实解除条件、要重做的验证：
`python3 scripts/project.py recover --project PROJECT --manager-idle --evidence RESOLUTION.md`
旧轮完整保留且不标 approved；回到初始化或同阶段修正。此命令是状态恢复，不授予权限，不可用于绕过平台拒绝。

经理迁移仅主管使用，先处理原 activeRound：
`python3 scripts/project.py replace_manager --project PROJECT --manager-idle --evidence HANDOVER.md --chat-url NEW_URL`
复用 GOAL/架构/历史，关闭 bootstrap 门槛，重新验证双向通信再实施。

目标循环遇到可解决问题应继续处理，遇到真实外部权限或用户决定则保存准确阻塞。没有宿主等待/唤醒能力时无法保证无人值守连续运行；本技能不伪造后台服务。

## 旧项目迁移与未发送轮次取消（schema v4）

先 `project.py status --project PROJECT`，核对 activeRound、lastAcceptedRound、真实会话和 receipt。不能根据过时交接取消已接收轮次。以下命令中的文件必须是本次实际检查记录；参数标志只是操作者声明，不是浏览器自动验证。

```sh
python3 scripts/project.py cancel_unsent --project PROJECT --round ROUND_ID --reason '取消原因' --manager-idle --evidence INSPECTION.md
python3 scripts/project.py migrate --project PROJECT --manager-idle --developer-idle --evidence MAINTENANCE.md
```

`cancel_unsent` 仅用于已核实未发送的轮次，包括未绑定 activeRound 的孤立旧 bootstrap。证据应包含检查时间、准确会话 URL、该 roundId 未出现在用户消息中、所有 receipt 位置及状态、经理空闲状态。没有 receipt 不能单独证明未发送；外部 receipt 也必须检查。命令拒绝有 outbox 输出、已接收或本轮内有 intent/submitted/uncertain 收据的情况，保留全部旧文件并追加 CANCELLED.json，不批准任何结果。

`migrate` 支持 v2/v3 → v4，仅在经理和开发者都已停止写入、无 activeRound 时执行。完整旧维护目录归档至 migration-archives；保留目标、原阶段与固定 URL，补齐模板，刷新协议和开发者合同，重新关闭 bootstrap 门槛。旧 complete 不会继承为主人已确认。迁移后先填完整架构/章程和模型配置，再重新握手；不能靠手改 JSON 开门。重复迁移不重复归档。迁移中途失败时停止开发，用 migration-archives 原件核对恢复，勿继续半迁移状态或删除档案。

## 异常恢复判定表

| 异常 | 必查证据 | 重试与保留规则 |
|---|---|---|
| 审核尚未发送 | 准确 URL、roundId 用户消息、所有 receipt、空 outbox、经理空闲 | 已确认未发送可发送原 PROMPT 一次；不再需要则 cancel_unsent。保留 REQUEST/SNAPSHOT/PROMPT |
| 发送结果未知（intent/uncertain） | 实际用户消息是否包含 roundId、网页忙碌状态、outbox、收据 | 不重发、不删收据。若已收到则等待；无法判定就 blocked。人工确认经理停止及解除条件后 recover，旧轮保留，新轮新 ID |
| 网页不可访问 | 原 URL、登录/网络状态、是否只是权限或工具不可用 | 先恢复原会话。不能推断经理已停止；无法确认则阻塞。主管确认停工后可 recover + replace_manager + bootstrap |
| 只写部分 outbox | 必需文件、DONE、nonce、实际网页是否还忙 | 忙则等待；停止后仅请求补完同轮缺件，不再发送原任务。已有内容保留，开发者不得代写 DONE；无法恢复时审计 recover |
| 审核期间源码变化 | SNAPSHOT 与当前文件哈希、新增/删除文件、控制文件哈希 | 拒绝 stale approved；不把源码改回以迎合旧审核。冻结新版本，经理停止后 recover，保留原审核并新快照重审 |

被平台安全检查拒绝的动作不能通过上述恢复路径重新包装执行。
