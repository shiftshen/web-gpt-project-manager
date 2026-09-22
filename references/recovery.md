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
