# 开发执行约定

你的接口是本项目绑定的网页开发经理，以及本目录的任务和验收文件。无需读取其他管理对话。

1. 开发前读 GOAL、CHARTER、ARCHITECTURE、PLAN、ACCEPTANCE、STATUS，确认当前阶段允许开始。
2. 每次只实施批准阶段；按任务单开发、测试、差异审查，保留其他改动。
3. reports 中按统一格式提交结果。失败、未运行、未验证要准确报告。
4. 阶段末向固定 PM URL 发送一次生成的 PROMPT；不重复开窗口，不在经理运行中打断。
5. approved 进入下一阶段；changes_requested 按同阶段意见修正；blocked/escalated 等待所需决策，不自行扩权。
6. 每阶段本地更新 PROGRESS；只有完成、实质阻塞、需要决定或最终就绪才发通知。
7. 最终经理审核通过后停止代码修改，等待最终验收；不能把任务状态自行改成 complete。
8. 不执行 supervisor_review、owner_confirm；这两个动作由对应验收角色依据真实证据执行。
