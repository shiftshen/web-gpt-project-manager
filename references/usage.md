# 用户只需提供项目目标与主管前缀

通用主管前缀保存在 templates/CODEX_SUPERVISOR_PROMPT.md。用户把它放在项目描述前；Codex 根据真实项目自动生成章程、架构、里程碑和协作环境，并交付经理 URL 与项目特定开发者提示词。

其他角色提示词由主管生成：
- 网页经理：project.py prepare 生成每轮 PROMPT.txt，加载项目内 PM_INSTRUCTIONS 与共同文件。
- 开发者：bootstrap 通过后 project.py developer_prompt 生成 DEVELOPER_PROMPT.md，统一 [ROLE]/[PROJECT]/[START]/[LOOP]/[REPORT]/[WAIT]/[BOUNDARIES]/[FINISH] 格式。

网页 GPT Work 使用用户指定的 GPT-6 Sol 基础模型，按实际 UI 验证，不擅自升级。每项目固定一个会话，不随阶段新建。开发者直接对接经理，最终停止在待终验，主管与用户决定最终接受。

本地模型不支持技能发现时，直接读取 ~/.codex/skills/web-gpt-project-manager/SKILL.md。把独立技能目录复制到其他宿主的技能目录即可，无需复制业务项目。网页通过 WebCodex 读取项目内 PM_INSTRUCTIONS，不要求全局插件安装。

Chrome 桥接仅 macOS 已登录 Chrome 实测；Ego Lite 桥接需要已有受管 task space，当前已在 macOS 实测页面读取，完整轮次仍逐项目验证。其他平台需当地实测；不可假称通用浏览器自动化已全平台验收。没有后台守护进程，没有自动定时；升级通知由共享文件保存，主管下次被调用时恢复读取。

## 两段式交付（固定）

1. `project.py handoff_prompt --project PROJECT`：输出第一段 DEVELOPER_HANDOFF_PROMPT，负责恢复和握手，可在初始化/阻塞时生成。
2. 完成实际 bootstrap/accept。已经有效的握手直接复用。
3. `project.py developer_prompt --project PROJECT`：返回 handoffPrompt 和 goalPrompt。先发第一段，再用第二段 DEVELOPER_GOAL_PROMPT 开目标模式；原 DEVELOPER_PROMPT 保留为完整合同。

第二段继承第一段的身份、权限、目标与会话，不能重置项目或扩大授权。握手未通过时不能生成放行的目标包。普通问题走 consult，由经理诊断；真实外部阻塞再升级。
