# 权限、升级和模型配置

| 变更 | 决策权限 |
|---|---|
| 任务排序、拆分/合并阶段、补测试、架构内局部实现替换 | 网页经理可批准；写清证据和计划版本 |
| 更换技术栈、持久化/交换数据格式、核心接口或兼容合同 | 升级主管，先提交影响、迁移/回退方案；批准后才能改架构基线 |
| 扩大功能范围、改变最终验收标准、预算或发布权限 | 主管对齐项目主人授权；经理不能自行批准 |
| 最终交付 | 经理就绪 → 主管独立验收 → 主人明确接受 |

主管授权必须有可引用记录；不能仅凭网页经理说“主管同意”。原始目标与最终标准只按主人授权更新。阶段 ACCEPTANCE 可以细化，不能删除、弱化 GOAL/CHARTER 的总体要求。

没有真实唤醒能力时：写 ESCALATIONS.md（编号、问题、证据、影响、选项、建议、待谁决定、恢复命令/轮次），在当前界面明确报告“待主管处理”。记录 notificationStatus=pending，不声称主管已收到通知。仅在实际发送并读回确认后可记录 delivered，仍不等于已决策。暂停依赖该决定的工作；已有授权且不受影响的工作可继续。

## 模型配置

MANAGER_CONFIG.json 纳入审核控制文件指纹。requested 是本次用户选择，observed 是浏览器实际 UI 及检查证据，两者必须分开。模板默认 Work / GPT-6 / default（基础档意图），不保证任意账号存在相同名称。用户本次选择优先，实际 UI 不可辨认时记录 unknown，按下述验证策略处理，不猜档位，不自动升级 Pro/更贵模型。

在空闲边界记录配置（本命令不操作网页，必须先实际检查）：

```sh
python3 scripts/project.py configure --project PROJECT --manager-idle --evidence UI-CHECK.md --mode Work --model GPT-6 --reasoning default --observed-mode Work --observed-model GPT-6 --observed-reasoning default
```

不一致时先报告并解决；不得把 default 当作已证实的基础档。配置变更保留旧配置审计并重新 bootstrap。模型选择不提供额度保证，技能不声称可取得完整计费记录。


## v0.3 验证策略与诊断通道

- `strict`：默认兼容原策略，要求 observed 与 requested 一致。先有边界地查看实际菜单；缺信息可咨询经理，不因常规只读菜单操作反复请求许可。
- `keep_existing`：用户明确授权沿用当前会话。保留真实 observed（包括 unknown 或已知差异），配置存入授权来源，允许握手和阶段沟通；不声称模型已核实、不切换、不增加预算。用户明确要求严格指定模型时不能自行用它放宽要求。
- 记录授权后 `configure ... --policy keep_existing --authorization USER-AUTHORIZATION.md`；其他必需参数与原 configure 相同。策略变化归档并重新 bootstrap；不直接手改 JSON。
- 新增 `prepare --kind consult`：固定经理的诊断通道，可在未握手或 strict 未核实时提交问题；不能越过平台拒绝、不能授权业务开发。接收诊断仅存 lastConsultRound，保留原计划与启动门槛，诊断 approved 回到咨询前状态，仍须落实真实解除条件；诊断 blocked 保持阻塞。不要为同一问题反复发相同咨询。
- 网页经理自称模型名不构成 UI 证据。旧 probe 不构成本轮连通实测。读取菜单失败不证明菜单在所有工具间必然关闭，更不能武断认定为产品限制。
