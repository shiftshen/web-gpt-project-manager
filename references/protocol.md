# 交接协议 v1

每轮存放于目标项目 .gpt-pm/rounds/<round-id>/：
- HANDOFF.md：本地开发者事实报告；属于待核验材料。
- SNAPSHOT.json：项目、WebCodex ID、显式选定文件集合及 SHA256。
- PROMPT.txt：发给网页 GPT 的最小请求。
- outbox/REVIEW.md：结论 approved / changes_requested / blocked；审查文件/行、严重级别、实跑命令、结果与证据局限。
- outbox/NEXT_TASK.md：目标、优先级、允许/禁止路径、具体交付、依赖、停止条件、预计工作量。按实际质量选任务，不硬编码 M5/M6。
- outbox/ACCEPTANCE.md：逐条验收条件，对应行为、命令、预期和失败判定；隔离测试副作用；不把 mock 当真实调用。
- outbox/DONE.json：最后写入的完成标记，字段 schemaVersion=1、roundId、status、snapshotSha256、producer="web-gpt-via-webcodex"、verifiedAt、testsRun 数组。连通性轮次另有 probeNonce。
- outbox/WEB_GPT_PROBE.txt：仅首次 probe 轮次由网页 GPT 创建，精确内容为 nonce 加换行。

只有写完所有文档后才写 DONE.json。若读到的源码和 SNAPSHOT 不一致，PM 输出 blocked 并说明变化，不能接受旧证据。离线快照只记录哈希与路径，不复制源码。

来源校验是协作协议，并非密码学身份认证：共享磁盘上其他程序也能写相同文件。首次测试通过“本地事先未创建 probe → 浏览器实际提交 → WebCodex 输出 → 本地读回”验证链路。

verify 将交付完整性与源码新鲜度分别返回：源码变化但 PM 正确写出完整 blocked 时，deliveryVerified=true、sourceUnchanged=false、actionable=false，可以接收阻塞报告。源码变化而 PM 声称 approved/changes_requested 则拒绝。缺少任何必需输出、轮次错误或 probe 不符始终拒绝；exit 0 只代表协议验证成功，必须读取 status 与 actionable，不等于授权继续开发。

审查时仅运行必要的验证。项目的真实调用预算、环境授权、发布权限不因交接而增加。下一轮开发使用文档中的目标，但先核对当前文件与原授权。

存档中可能含项目名称和公开路径，不放密钥、Cookie、完整环境变量。报告作者负责脱敏；脚本拒绝典型敏感文件名，但不能检测所有秘密。数据保留在用户选定项目内，不自动上传代码到其他服务；网页 GPT 按授权通过 WebCodex 访问。
