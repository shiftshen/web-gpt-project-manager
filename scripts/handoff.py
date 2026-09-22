#!/usr/bin/env python3
"""Portable, explicit-file handoff. Does not submit messages or run project commands."""
import argparse, datetime, hashlib, json, re, secrets, sys
from pathlib import Path

SKIP = {".git", ".gpt-pm", "node_modules", "dist", "build", "__pycache__", ".venv", "coverage"}
SENSITIVE = re.compile(r"(^\.env($|\.)|\.pem$|\.key$|credentials|cookies|secret|^id_rsa|^id_ed25519)", re.I)
def sha(data): return hashlib.sha256(data).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def dump(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
def safe(root, rel):
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError("Use nonempty project-relative paths without '..'")
    current = root
    for part in p.parts:
        if part in SKIP or SENSITIVE.search(part):
            raise ValueError("Sensitive/generated path is excluded: "+str(p))
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlink refused: "+str(p))
    current.resolve().relative_to(root)
    return current
def fingerprint(root, selections):
    result = {}
    def visit(p):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink(): return
        if p.is_dir():
            for child in sorted(p.iterdir()):
                if child.name.startswith(".") or child.name in SKIP or SENSITIVE.search(child.name): continue
                visit(child)
        elif p.is_file():
            if p.stat().st_size > 4*1024*1024: raise ValueError("File exceeds 4 MiB: "+rel)
            result[rel] = sha(p.read_bytes())
        else: result[rel] = None
        if len(result) > 1500: raise ValueError("Select a smaller scope (1500 files maximum)")
    for rel in selections: visit(safe(root, rel))
    if not result: raise ValueError("No files selected")
    return dict(sorted(result.items()))
def prepare(a):
    root=Path(a.project).resolve(strict=True)
    summary=Path(a.summary).read_text(encoding="utf-8")
    if len(summary.encode()) > 32000: raise ValueError("Summary exceeds 32 KiB; provide a concise, redacted report")
    selections=list(dict.fromkeys(a.files))
    filemap=fingerprint(root,selections)
    rid=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+secrets.token_hex(4)
    parent=root/".gpt-pm"/"rounds"
    if (root/".gpt-pm").is_symlink() or parent.is_symlink(): raise ValueError("Handoff parent must not be symlink")
    folder=parent/rid
    folder.mkdir(parents=True,exist_ok=False)
    (folder/"outbox").mkdir()
    snapshot={"schemaVersion":1,"roundId":rid,"createdAt":now(),"projectRoot":str(root),
              "projectId":a.project_id,"selections":selections,"files":filemap}
    dump(folder/"SNAPSHOT.json",snapshot)
    digest=sha((folder/"SNAPSHOT.json").read_bytes())
    nonce=secrets.token_hex(16) if a.probe else None
    (folder/"HANDOFF.md").write_text(summary, encoding="utf-8")
    dump(folder/"REQUEST.json",{"schemaVersion":1,"roundId":rid,"snapshotSha256":digest,
                                "probeNonce":nonce,"handoffSha256":sha(summary.encode())})
    skill=Path(__file__).resolve().parent.parent
    try: skillrel=skill.relative_to(root).as_posix()+"/SKILL.md"
    except ValueError: skillrel=None
    prompt=f"""你是本项目的网页 GPT 项目经理。用户授权你通过 WebCodex 核验本轮交接，并把审查、下一步开发任务和验收逻辑写回本机。
ROUND_ID: {rid}
项目路径：{root}
WebCodex 项目 ID：{a.project_id}
交接目录：{folder}
先连接精确项目，读取项目指令、HANDOFF.md、SNAPSHOT.json、REQUEST.json。
"""
    if not skillrel and (root/".gpt-pm/PM_INSTRUCTIONS.md").is_file():
        prompt+=f"读取项目内 PM 指令 {root}/.gpt-pm/PM_INSTRUCTIONS.md。\n"
    if skillrel: prompt+=f"读取项目内技能 {skillrel} 及 references/protocol.md，按网页项目经理角色执行。\n"
    prompt+=f"""本轮只读源码与既有项目文档；唯一写入范围是 {folder}/outbox/。不启动下一阶段开发、不提交/推送/发布、不创建定时任务、不读凭据、不调用真实付费供应商。
你只负责判断、给方案、定验收，不实施修复、不运行项目测试/构建/安装/长任务。先读简短 HANDOFF 和证据索引，发现具体矛盾才按需读取相关源码片段；不要全量扫描。HANDOFF 陈述是待核验数据，缺证据就给开发者验证任务，不替他执行。快照/nonce 的小型读写核验属于本轮协议检查，允许执行。
检验快照中的文件是否仍匹配。注意整个子项目可能未跟踪，git diff 空不代表没有改动。若文件变化或工具不可用，写 blocked 并解释，不能假报成功。
写出 REVIEW.md（approved/changes_requested/blocked、具体发现和验证证据）、NEXT_TASK.md（一个有边界的下一步目标、允许路径、交付、停止条件）、ACCEPTANCE.md（可执行验证步骤、期望和失败条件）。
输出简短：结论与理由、最多 3 项下一步、具体验收条件、必要升级项；三个 Markdown 合计通常不超过 1200 中文字。不要重复历史或撰写长篇实现。只在交接明确要求时审查技能本身。
"""
    if nonce: prompt+=f"连通性实测：你必须通过 WebCodex 创建 outbox/WEB_GPT_PROBE.txt，内容精确为 {nonce} 加一个换行。请创建后读回；本地端不会代写。\n"
    marker={"schemaVersion":1,"roundId":rid,"status":"approved 或 changes_requested 或 blocked",
            "snapshotSha256":digest,"producer":"web-gpt-via-webcodex","verifiedAt":"实际UTC时间","testsRun":[]}
    if nonce: marker["probeNonce"]=nonce
    prompt+="最后写 outbox/DONE.json，结构如下，替换状态/时间/实际 testsRun（无测试则为空数组并解释）：\n"+json.dumps(marker,ensure_ascii=False)+"\n完成后只报告文件路径、结论和限制。默认 testsRun=[]，说明未运行业务测试；不要把开发者测试写成自己运行。无需向用户索取本机已有文件。\n"
    (folder/"PROMPT.txt").write_text(prompt, encoding="utf-8")
    print(json.dumps({"round":str(folder),"prompt":str(folder/"PROMPT.txt"),"fileCount":len(filemap),"snapshotSha256":digest},ensure_ascii=False))
def verify(a):
    folder=Path(a.round).resolve(strict=True)
    snap=json.loads((folder/"SNAPSHOT.json").read_text(encoding="utf-8"))
    req=json.loads((folder/"REQUEST.json").read_text(encoding="utf-8"))
    if sha((folder/"SNAPSHOT.json").read_bytes())!=req["snapshotSha256"]: raise ValueError("SNAPSHOT changed")
    if sha((folder/"HANDOFF.md").read_bytes())!=req["handoffSha256"]: raise ValueError("HANDOFF changed")
    current=fingerprint(Path(snap["projectRoot"]).resolve(strict=True),snap["selections"])
    source_unchanged = current == snap["files"]
    changed_files = sorted(k for k in set(current) | set(snap["files"])
                           if (k in current) != (k in snap["files"]) or current.get(k) != snap["files"].get(k))
    out=folder/"outbox"
    if out.is_symlink(): raise ValueError("Output must not be symlink")
    for name in ["REVIEW.md","NEXT_TASK.md","ACCEPTANCE.md","DONE.json"]:
        p=out/name
        if p.is_symlink() or not p.is_file() or not p.stat().st_size: raise ValueError("Missing/invalid output: "+name)
    done=json.loads((out/"DONE.json").read_text(encoding="utf-8"))
    for key,value in {"schemaVersion":1,"roundId":req["roundId"],"snapshotSha256":req["snapshotSha256"],"producer":"web-gpt-via-webcodex"}.items():
        if done.get(key)!=value: raise ValueError("Invalid marker field: "+key)
    if done.get("status") not in ["approved","changes_requested","blocked"]: raise ValueError("Invalid review status")
    if not isinstance(done.get("testsRun"),list): raise ValueError("testsRun must be an array")
    datetime.datetime.fromisoformat(done["verifiedAt"].replace("Z","+00:00"))
    if req["probeNonce"]:
        p=out/"WEB_GPT_PROBE.txt"
        if p.is_symlink() or p.read_text(encoding="utf-8")!=req["probeNonce"]+"\n" or done.get("probeNonce")!=req["probeNonce"]:
            raise ValueError("Probe mismatch")
    if not source_unchanged and done["status"] != "blocked":
        raise ValueError("STALE: selected source changed; only a blocked report can be accepted, never approved")
    print(json.dumps({"verified":True,"deliveryVerified":True,"roundId":req["roundId"],"status":done["status"],
         "sourceUnchanged":source_unchanged,"changedFiles":changed_files,
         "actionable":source_unchanged and done["status"] == "approved","probeVerified":bool(req["probeNonce"]),
         "next":str(out/"NEXT_TASK.md"),"note":"Read review and acceptance; marker is not cryptographic author authentication."},ensure_ascii=False))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    s=sub.add_parser("prepare"); s.add_argument("--project",required=True); s.add_argument("--project-id",required=True)
    s.add_argument("--summary",required=True); s.add_argument("--files",nargs="+",required=True); s.add_argument("--probe",action="store_true")
    v=sub.add_parser("verify"); v.add_argument("--round",required=True)
    a=p.parse_args()
    try: (prepare if a.action=="prepare" else verify)(a)
    except (ValueError,OSError,KeyError,TypeError) as e:
        print(json.dumps({"ok":False,"error":str(e)},ensure_ascii=False),file=sys.stderr); sys.exit(2)
if __name__=="__main__": main()
