# 用户只需提供项目目标与主管前缀

通用主管前缀保存在 templates/CODEX_SUPERVISOR_PROMPT.md。用户把它放在项目描述前；Codex 根据真实项目自动生成章程、架构、里程碑和协作环境，并交付经理 URL 与项目特定开发者提示词。

其他角色提示词由主管生成：
- 网页经理：project.py prepare 生成每轮 PROMPT.txt，加载项目内 PM_INSTRUCTIONS 与共同文件。
- 开发者：bootstrap 通过后 project.py developer_prompt 生成 DEVELOPER_PROMPT.md，统一 [ROLE]/[PROJECT]/[START]/[LOOP]/[REPORT]/[WAIT]/[BOUNDARIES]/[FINISH] 格式。

网页 GPT Work 使用用户指定的 GPT-6 基础模型，按实际 UI 验证，不擅自升级。每项目固定一个会话，不随阶段新建。开发者直接对接经理，最终停止在待终验，主管与用户决定最终接受。

本地模型不支持技能发现时，直接读取 ~/.codex/skills/web-gpt-project-manager/SKILL.md。把独立技能目录复制到其他宿主的技能目录即可，无需复制业务项目。网页通过 WebCodex 读取项目内 PM_INSTRUCTIONS，不要求全局插件安装。

浏览器脚本仅 macOS 已登录 Chrome 实测，其他平台需用当地可用浏览器工具；不可假称通用浏览器自动化已经全平台验收。没有后台守护进程，没有自动定时；升级通知由共享文件保存，主管下次被调用时恢复读取。
