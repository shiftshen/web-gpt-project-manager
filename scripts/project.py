#!/usr/bin/env python3
"""Per-project PM lifecycle. No model calls, scheduler, Git writes, or browser messages."""
import argparse, contextlib, hashlib, io, json, re, sys, shutil, uuid
from pathlib import Path
import handoff as h

CHAT = re.compile(r'^https://chatgpt\.com/c/[A-Za-z0-9-]+$')
CONTROL = ['GOAL.md','CHARTER.md','ARCHITECTURE.md','MILESTONES.md','PLAN.md','ACCEPTANCE.md','PM_INSTRUCTIONS.md','MANAGER_CONFIG.json']

def save(path,data):
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n', encoding="utf-8")
    temp.replace(path)

def paths(project):
    root=Path(project).resolve(strict=True)
    pm=root/'.gpt-pm'
    if pm.is_symlink(): raise ValueError('Project PM directory must not be symlink')
    return root,pm

def state(project):
    root,pm=paths(project)
    p=pm/'PROJECT.json'
    if p.is_symlink(): raise ValueError('PROJECT.json must not be symlink')
    data=json.loads(p.read_text(encoding="utf-8"))
    if data['projectRoot']!=str(root): raise ValueError('Project root mismatch; do not reuse another project state')
    return root,pm,data

def output(data): print(json.dumps(data,ensure_ascii=False,indent=2))
def update(pm,data,event):
    data['updatedAt']=h.now()
    save(pm/'PROJECT.json',data)
    (pm/'STATUS.md').write_text('# 当前阶段状态\n\n'+json.dumps({k:data.get(k) for k in ['status','stage','chatUrl','activeRound','lastAcceptedRound','bootstrapApproved','updatedAt']},ensure_ascii=False,indent=2)+'\n', encoding="utf-8")
    with (pm/'DECISIONS.md').open('a') as f: f.write('\n- '+data['updatedAt']+' '+event+'\n')

def init(a):
    root,pm=paths(a.project)
    goal=Path(a.goal_file).read_text(encoding="utf-8").strip()
    if not goal: raise ValueError('Goal must be explicit and nonempty')
    if a.chat_url and not CHAT.fullmatch(a.chat_url): raise ValueError('Expected exact ChatGPT /c/ conversation URL')
    if (pm/'PROJECT.json').exists():
        _,_,data=state(a.project)
        if data['projectId']!=a.project_id or (pm/'GOAL.md').read_text(encoding="utf-8").strip()!=goal:
            raise ValueError('Existing project goal/ID differs; preserve it and reconcile with the user')
        output(data);return
    pm.mkdir(exist_ok=True)
    contents={'GOAL.md':goal+'\n','PLAN.md':'# 阶段计划\n\n尚未通过项目经理启动审核。先验证沟通、确认里程碑和首阶段。\n',
              'ACCEPTANCE.md':'# 验收标准\n\n依据 GOAL，由项目经理在 bootstrap 轮写回明确标准；不得提前声称已验收。\n',
              'STATUS.md':'# 初始化\n','DECISIONS.md':'# 共同决策记录\n',
              'PM_INSTRUCTIONS.md':(Path(__file__).resolve().parent.parent/'references/pm.md').read_text(encoding="utf-8")}
    templates=Path(__file__).resolve().parent.parent/'templates'
    for name in ['CHARTER.md','ARCHITECTURE.md','MILESTONES.md','PROGRESS.md','ESCALATIONS.md','FINAL_REPORT.md','DEVELOPER_CONTRACT.md']:
        contents[name]=(templates/name).read_text(encoding="utf-8")
    for name in contents:
        if (pm/name).exists() or (pm/name).is_symlink(): raise ValueError('Refusing overwrite existing shared file: '+name)
    for name,content in contents.items(): (pm/name).write_text(content, encoding="utf-8")
    for name in ['reports','evidence','supervisor','owner']:
        (pm/name).mkdir(exist_ok=True)
    (pm/'reports/STAGE_REPORT_TEMPLATE.md').write_text((templates/'STAGE_REPORT.md').read_text(encoding="utf-8"), encoding="utf-8")
    data={'schemaVersion':4,'projectRoot':str(root),'projectId':a.project_id,'chatUrl':a.chat_url,
          'status':'initializing','stage':0,'planRevision':1,'bootstrapApproved':False,'activeRound':None,
          'lastAcceptedRound':None,'supervisorApproved':False,'ownerAccepted':False,'createdAt':h.now()}
    save(pm/'MANAGER_CONFIG.json',default_config())
    update(pm,data,'初始化固定网页项目经理；尚未启动目标开发。')
    output(data)

def bind(a):
    _,pm,data=state(a.project)
    if not CHAT.fullmatch(a.chat_url): raise ValueError('Expected exact ChatGPT /c/ conversation URL')
    if data.get('chatUrl') and data['chatUrl']!=a.chat_url:
        raise ValueError('Different PM already bound; do not silently replace project manager')
    data['chatUrl']=a.chat_url
    update(pm,data,'绑定固定 PM 会话 '+a.chat_url)
    output(data)

def controls(pm):
    result={}
    for name in CONTROL:
        p=pm/name
        if p.is_symlink(): raise ValueError('Shared control file must not be symlink: '+name)
        result[name]=h.sha(p.read_bytes())
    return result

def begin(a):
    _,pm,data=state(a.project)
    if data.get('schemaVersion')!=4: raise ValueError('Migrate legacy project before new work')
    if not data['bootstrapApproved'] or data['status'] not in ['ready','changes_requested'] or data['activeRound']:
        raise ValueError('GATE_CLOSED: complete bootstrap/stage review first')
    if data['status']=='ready': data['stage']+=1
    data['status']='running'
    update(pm,data,'开始阶段 '+str(data['stage'])+'；按共同 PLAN/ACCEPTANCE 实施。')
    output(data)

def prepare(a):
    root,pm,data=state(a.project)
    if data.get('schemaVersion')!=4: raise ValueError('Migrate legacy project before preparing new rounds')
    if data['activeRound']: raise ValueError('Pending round exists; resume it instead of duplicate submission')
    config=json.loads((pm/'MANAGER_CONFIG.json').read_text(encoding='utf-8'))
    observed=config.get('observed') or {}
    policy=config.get('verificationPolicy','strict')
    unresolved=any(not observed.get(k) or observed.get(k) in ['unknown','unverified'] or observed.get(k)!=v for k,v in config['requested'].items()) or not observed.get('evidence')
    if a.kind!='consult' and unresolved and not (policy=='keep_existing' and config.get('policyAuthorization') and observed.get('evidence')):
        raise ValueError('Manager configuration not verified/matched; inspect UI, consult PM, or record user-authorized keep_existing policy')
    if a.kind=='consult':
        if not data.get('chatUrl') or data['status'] in ['complete','supervisor_review_pending','owner_acceptance_pending']:
            raise ValueError('Consult requires bound PM and an unfinished development phase')
    elif a.kind=='bootstrap':
        if data['bootstrapApproved'] or data['status'] not in ['initializing','blocked','changes_requested']:
            raise ValueError('Bootstrap already approved or wrong state')
    elif not data['bootstrapApproved'] or data['status'] not in ['running','ready','changes_requested','blocked']:
        raise ValueError('GATE_CLOSED: bootstrap must pass before stage/final submission')
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):
        h.prepare(argparse.Namespace(project=str(root),project_id=data['projectId'],summary=a.summary,files=a.files,probe=a.kind=='bootstrap'))
    info=json.loads(capture.getvalue());folder=Path(info['round'])
    req=json.loads((folder/'REQUEST.json').read_text(encoding="utf-8"))
    req.update(kind=a.kind,stage=data['stage'],projectRoot=str(root),projectId=data['projectId'],controlHashes=controls(pm),priorStatus=data['status'])
    save(folder/'REQUEST.json',req)
    prompt=(folder/'PROMPT.txt').read_text(encoding="utf-8")
    prompt+='\n这是固定项目经理会话的 '+a.kind+' 轮，阶段 '+str(data['stage'])+'。\n'
    prompt+='先读取 '+str(pm/'PM_INSTRUCTIONS.md')+' 和 MANAGER_CONFIG.json（requested 是用户选择，observed 是实际 UI 证据；strict 要求一致；有用户授权的 keep_existing 保持当前会话，unknown 不冒充核实；consult 仅诊断，不擅自升级）、GOAL.md、CHARTER.md、ARCHITECTURE.md、MILESTONES.md、PLAN.md、ACCEPTANCE.md、STATUS.md、DECISIONS.md。按 REQUEST.controlHashes 核验共同控制文件。\n'
    prompt+='当前绑定会话：'+str(data['chatUrl'] or '首次启动，发送后本地绑定真实会话URL')+'；后续阶段沿用本会话。\n'
    if a.kind=='consult': prompt+='本轮仅问题咨询：诊断 HANDOFF 的阻塞，给出原权限内恢复方案；approved 只表示建议完整，不批准实施，不通过 bootstrap，不授予权限。无法解决才列出需要主管/主人的最小决定。不要自报模型身份当作 UI 证据。\n'
    if a.kind=='bootstrap': prompt+='本轮先确认目标完成标准、里程碑、首阶段任务和验收，再完成双向 probe。尚未允许本地开始正式目标开发。\n'
    if a.kind=='replan': prompt+='本轮为基于证据的动态重规划：说明原方案为何不适用、替代方案和最小验证，允许在章程与架构授权边界内调整阶段拆分/顺序/实现方法；不改变用户结果目标与完成标准。超出边界给出升级建议，不擅自授权。\n'
    if a.kind=='final': prompt+='经理只能判定已具备提交最终验收的条件；不得宣布项目最终完成。这是总体目标终验：逐条核对 GOAL，不把阶段完成当总体完成。DONE.json 增加 goalComplete 布尔值；全部必需目标完成才 approved 且 true。\n'
    (folder/'PROMPT.txt').write_text(prompt, encoding="utf-8")
    data.update(status='awaiting_review',activeRound=folder.name)
    update(pm,data,'准备 '+a.kind+' 审核 '+folder.name+'；被审文件冻结，等待 PM 回传。')
    info['chatUrl']=data['chatUrl'];info['kind']=a.kind
    output(info)

def accept(a):
    root,pm,data=state(a.project)
    rid=data.get('activeRound')
    if not rid: raise ValueError('No pending round')
    if not data.get('chatUrl'): raise ValueError('Bind actual browser conversation URL first')
    folder=pm/'rounds'/rid
    req=json.loads((folder/'REQUEST.json').read_text(encoding="utf-8"))
    snap=json.loads((folder/'SNAPSHOT.json').read_text(encoding="utf-8"))
    if req['roundId']!=rid or snap['roundId']!=rid or snap['projectRoot']!=str(root) or snap['projectId']!=data['projectId']:
        raise ValueError('Wrong round/project; never consume another project review')
    if controls(pm)!=req['controlHashes']: raise ValueError('Shared goal/plan/acceptance changed during review; reconcile before proceeding')
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture): h.verify(argparse.Namespace(round=str(folder)))
    result=json.loads(capture.getvalue())
    done=json.loads((folder/'outbox/DONE.json').read_text(encoding="utf-8"))
    status=result['status']
    if req['kind']=='consult':
        data.update(activeRound=None,lastConsultRound=rid,status=req.get('priorStatus','blocked') if status=='approved' else 'blocked')
        update(pm,data,'收到诊断建议 '+rid+'；不改变计划、不批准开发、不重置连续返工记录。')
        output({'state':data,'review':result,'consultOnly':True});return
    if req['kind']=='final' and status=='approved' and done.get('goalComplete') is not True:
        raise ValueError('Final approval requires explicit goalComplete=true and human-readable evidence')
    if status=='approved':
        if req['kind']=='replan': data['planRevision']=data.get('planRevision',1)+1
        if req['kind']=='bootstrap':
            if not result['probeVerified']: raise ValueError('Bootstrap probe required')
            data['bootstrapApproved']=True
        data['status']='supervisor_review_pending' if req['kind']=='final' else 'ready'
        if req['kind']=='final': data['finalRound']=rid
    else: data['status']=status
    if status=='changes_requested':
        data['reworkCount']=data.get('reworkCount',0)+1
        if data['reworkCount']>=2:
            data['status']='escalated'
            with (pm/'ESCALATIONS.md').open('a') as f:
                f.write('\n连续两轮要求返工：'+rid+'；需主管纠偏后恢复，勿无限返工。\n')
    elif status=='approved': data['reworkCount']=0
    # Preserve PM originals. These shared files always identify their source round.
    (pm/'PLAN.md').write_text('# 当前任务（来源轮次 '+rid+'）\n\n'+(folder/'outbox/NEXT_TASK.md').read_text(encoding="utf-8"), encoding="utf-8")
    (pm/'ACCEPTANCE.md').write_text('# 当前验收（来源轮次 '+rid+'）\n\n'+(folder/'outbox/ACCEPTANCE.md').read_text(encoding="utf-8"), encoding="utf-8")
    if req['kind']=='final' and status=='approved': data['finalControlHashes']=controls(pm)
    data.update(lastAcceptedRound=rid,activeRound=None)
    update(pm,data,'收到 '+rid+'：'+status+'；sourceUnchanged='+str(result['sourceUnchanged']))
    output({'state':data,'review':result})

def blocked(a):
    _,pm,data=state(a.project)
    if not a.reason.strip(): raise ValueError('Concrete blocked reason required')
    data['status']='blocked'
    # Do not discard a possibly still running PM round or permit blind resubmission.
    update(pm,data,'阻塞（未通过审核，保留当前轮次）：'+a.reason)
    output(data)

def render_prompt(root,pm,data,template_name,target_name):
    template=(Path(__file__).resolve().parent.parent/'templates'/template_name).read_text(encoding='utf-8')
    text=template.replace('{{PROJECT_ROOT}}',str(root)).replace('{{PROJECT_ID}}',data['projectId']).replace('{{CHAT_URL}}',data['chatUrl'])
    (pm/target_name).write_text(text,encoding='utf-8')
    return str(pm/target_name)

def handoff_prompt(a):
    root,pm,data=state(a.project)
    if not data.get('chatUrl'): raise ValueError('Bind actual manager URL before handoff')
    path=render_prompt(root,pm,data,'DEVELOPER_HANDOFF_PROMPT.md','DEVELOPER_HANDOFF_PROMPT.md')
    output({'managerUrl':data['chatUrl'],'handoffPrompt':path,'goalReleased':False,'status':data['status']})

def developer_prompt(a):
    root,pm,data=state(a.project)
    if not data.get('bootstrapApproved') or not data.get('chatUrl') or data.get('activeRound'):
        raise ValueError('Cannot issue developer launch prompt before verified bootstrap / while review pending')
    if data['status'] not in ['ready','running','changes_requested']:
        raise ValueError('Project is not released for development')
    handoff=render_prompt(root,pm,data,'DEVELOPER_HANDOFF_PROMPT.md','DEVELOPER_HANDOFF_PROMPT.md')
    contract=render_prompt(root,pm,data,'DEVELOPER_PROMPT.md','DEVELOPER_PROMPT.md')
    goal=render_prompt(root,pm,data,'DEVELOPER_GOAL_PROMPT.md','DEVELOPER_GOAL_PROMPT.md')
    output({'projectRoot':str(root),'managerUrl':data['chatUrl'],'handoffPrompt':handoff,
            'goalPrompt':goal,'developerPrompt':contract,'goalReleased':True,'status':data['status']})

def final_fresh(pm,data):
    if controls(pm)!=data['finalControlHashes']: raise ValueError('Final goal/architecture/plan changed after PM approval')
    folder=pm/'rounds'/data['finalRound']
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture): h.verify(argparse.Namespace(round=str(folder)))
    result=json.loads(capture.getvalue())
    if not result['actionable']: raise ValueError('Final code evidence no longer current')
    return result

def supervisor_review(a):
    root,pm,data=state(a.project)
    if data['status'] not in ['supervisor_review_pending','escalated']:
        raise ValueError('Supervisor review only at escalation/final gate')
    report=Path(a.report).read_text(encoding="utf-8").strip()
    if not report: raise ValueError('Independent supervisor report required')
    final=data['status']=='supervisor_review_pending'
    if final and a.decision=='approved': final_fresh(pm,data)
    target=pm/'supervisor'/('review-'+h.now().replace(':','-')+'.md')
    target.write_text(report+'\n', encoding="utf-8")
    if final and a.decision=='approved':
        data.update(status='owner_acceptance_pending',supervisorApproved=True,supervisorReport=str(target),supervisorReportSha256=h.sha(target.read_bytes()))
    else:
        data.update(status='changes_requested',supervisorApproved=False,reworkCount=0)
    update(pm,data,'主管独立审查：'+a.decision+'；报告 '+str(target.relative_to(pm)))
    output(data)

def owner_confirm(a):
    _,pm,data=state(a.project)
    if data['status']!='owner_acceptance_pending' or not data.get('supervisorApproved'):
        raise ValueError('Owner confirmation requires supervisor approval first')
    final_fresh(pm,data)
    if h.sha(Path(data['supervisorReport']).read_bytes())!=data['supervisorReportSha256']:
        raise ValueError('Supervisor report changed')
    confirmation=Path(a.confirmation).read_text(encoding="utf-8").strip()
    if not confirmation: raise ValueError('Actual explicit owner confirmation must be recorded')
    target=pm/'owner/ACCEPTANCE.md'
    target.write_text(confirmation+'\n', encoding="utf-8")
    data.update(status='complete',ownerAccepted=True,ownerConfirmation=str(target))
    update(pm,data,'记录项目主人的明确验收确认，项目完成。')
    output(data)

def recover(a):
    _,pm,data=state(a.project)
    if not a.manager_idle: raise ValueError('Confirm actual browser manager has stopped before recovery')
    if data['status'] not in ['blocked','awaiting_review']:
        raise ValueError('Recovery applies only to blocked/pending rounds')
    evidence=Path(a.evidence).read_text(encoding="utf-8").strip()
    if not evidence: raise ValueError('Actual diagnosis and resolved-condition evidence required')
    rid=data.get('activeRound')
    record={'recordedAt':h.now(),'retiredRound':rid,'evidence':evidence,'approved':False}
    target=pm/'reports'/('recovery-'+h.now().replace(':','-')+'.json')
    save(target,record)
    data.update(activeRound=None,status='changes_requested' if data['bootstrapApproved'] else 'initializing')
    update(pm,data,'恢复记录 '+str(target.relative_to(pm))+'；旧轮保留且未批准，必须重新提交有效快照。')
    output(data)

def replace_manager(a):
    _,pm,data=state(a.project)
    if not a.manager_idle or data.get('activeRound'):
        raise ValueError('Retire pending work before explicit PM replacement')
    if not CHAT.fullmatch(a.chat_url): raise ValueError('Expected exact ChatGPT /c/ URL')
    if data['status']=='complete':raise ValueError('Completed project requires a new authorized goal')
    evidence=Path(a.evidence).read_text(encoding="utf-8").strip()
    if not evidence:raise ValueError('Supervisor handover record required')
    target=pm/'supervisor'/('handover-'+h.now().replace(':','-')+'.md')
    target.write_text(evidence+'\n', encoding="utf-8")
    old=data.get('chatUrl')
    data.update(chatUrl=a.chat_url,bootstrapApproved=False,status='initializing')
    update(pm,data,'主管迁移经理 '+str(old)+' -> '+a.chat_url+'；需重新 bootstrap，保留全部历史。')
    output(data)


def default_config():
    return {'requested':{'mode':'Work','model':'GPT-6','reasoning':'default'},
            'observed':None,'allowAutomaticUpgrade':False}

def audit_evidence(a):
    if not a.manager_idle: raise ValueError('Confirm manager idle; never interrupt active work')
    evidence=Path(a.evidence).read_text(encoding='utf-8').strip()
    if not evidence: raise ValueError('Nonempty inspection evidence required')
    return evidence

def cancel_unsent(a):
    _,pm,data=state(a.project)
    evidence=audit_evidence(a)
    if not a.reason.strip(): raise ValueError('Cancellation reason required')
    rid=a.round
    if not re.fullmatch(r'[A-Za-z0-9_-]+',rid): raise ValueError('Invalid round ID')
    folder=pm/'rounds'/rid
    if folder.is_symlink() or not folder.is_dir(): raise ValueError('Missing or unsafe round')
    if any(x.is_symlink() for x in folder.rglob('*')): raise ValueError('Unsafe symlink in round')
    if data.get('activeRound') not in [None,rid]: raise ValueError('Another round is active')
    if data.get('lastAcceptedRound')==rid: raise ValueError('Cannot cancel accepted round')
    if (folder/'CANCELLED.json').exists(): raise ValueError('Round already cancelled; preserve audit')
    # An empty outbox and absent receipt alone do NOT prove that a message was unsent.
    if any((folder/'outbox').iterdir()): raise ValueError('PM output exists; use diagnosis/recover, not cancel_unsent')
    for receipt in folder.rglob('*.json'):
        obj=json.loads(receipt.read_text(encoding='utf-8'))
        if isinstance(obj,dict) and (obj.get('status') in ['intent','submitted','uncertain'] or obj.get('state') in ['intent','submitted','uncertain']):
            raise ValueError('Send receipt exists; resolve unknown/sent delivery using recover')
    save(folder/'CANCELLED.json',{'roundId':rid,'reason':a.reason,'evidence':evidence,
         'recordedAt':h.now(),'deliveryAssessment':'confirmed_unsent','approved':False})
    if data.get('activeRound')==rid:
        data.update(activeRound=None,status='changes_requested' if data.get('bootstrapApproved') else 'initializing')
    update(pm,data,'取消经浏览器核实未发送轮次 '+rid+'：'+a.reason+'；保留原始记录。')
    output(data)

def migrate(a):
    _,pm,data=state(a.project)
    evidence=audit_evidence(a)
    version=data.get('schemaVersion')
    if version==4: output(data);return
    if version not in [2,3]: raise ValueError('Only schema v2/v3 can migrate')
    if data.get('activeRound'): raise ValueError('Resolve active round before migration; never overwrite it')
    if not a.developer_idle: raise ValueError('Pause developer writes in an agreed maintenance window')
    # Reject links before backup or writes. Archive all old controls, receipts and output.
    if any(x.is_symlink() for x in pm.rglob('*')): raise ValueError('Symlink in legacy state; inspect before migration')
    backup=pm/'migration-archives'/('v'+str(version)+'-'+uuid.uuid4().hex)
    backup.mkdir(parents=True)
    for source in list(pm.iterdir()):
        if source.name=='migration-archives': continue
        target=backup/source.name
        if source.is_dir(): shutil.copytree(source,target)
        else: shutil.copy2(source,target)
    save(backup/'MIGRATION.json',{'from':version,'to':4,'recordedAt':h.now(),'evidence':evidence,'approved':False})
    base=Path(__file__).resolve().parent.parent
    for name in ['reports','evidence','supervisor','owner']: (pm/name).mkdir(exist_ok=True)
    for name in ['CHARTER.md','ARCHITECTURE.md','MILESTONES.md','PROGRESS.md','ESCALATIONS.md','FINAL_REPORT.md']:
        if not (pm/name).exists(): shutil.copy2(base/'templates'/name,pm/name)
    shutil.copy2(base/'templates/DEVELOPER_CONTRACT.md',pm/'DEVELOPER_CONTRACT.md')
    shutil.copy2(base/'templates/STAGE_REPORT.md',pm/'reports/STAGE_REPORT_TEMPLATE.md')
    shutil.copy2(base/'references/pm.md',pm/'PM_INSTRUCTIONS.md')
    config=json.loads((pm/'MANAGER_CONFIG.json').read_text(encoding='utf-8')) if (pm/'MANAGER_CONFIG.json').exists() else default_config()
    config['observed']=None
    save(pm/'MANAGER_CONFIG.json',config)
    data.update(schemaVersion=4,status='initializing',bootstrapApproved=False,supervisorApproved=False,
                ownerAccepted=False,activeRound=None,planRevision=data.get('planRevision',1),
                migrationArchive=str(backup.relative_to(pm)))
    update(pm,data,'迁移 v'+str(version)+' → v4；保留目标、绑定和历史，重新 bootstrap，不继承最终批准。')
    output(data)

def configure(a):
    _,pm,data=state(a.project)
    evidence=audit_evidence(a)
    if data.get('activeRound') or data['status'] not in ['initializing','ready','changes_requested','blocked']:
        raise ValueError('Configure only at idle boundary, outside pending/final review')
    config={'requested':{'mode':a.mode,'model':a.model,'reasoning':a.reasoning},
            'observed':{'mode':a.observed_mode,'model':a.observed_model,'reasoning':a.observed_reasoning,
                        'evidence':evidence,'recordedAt':h.now()},'allowAutomaticUpgrade':False}
    policy=getattr(a,'policy','strict')
    if policy not in ['strict','keep_existing']: raise ValueError('Invalid verification policy')
    authorization=getattr(a,'authorization',None)
    if policy=='keep_existing':
        if not authorization: raise ValueError('keep_existing requires actual user authorization record')
        record=Path(authorization).read_text(encoding='utf-8').strip()
        if not record: raise ValueError('Nonempty authorization record required')
        config['policyAuthorization']=record
    config['verificationPolicy']=policy
    old=json.loads((pm/'MANAGER_CONFIG.json').read_text(encoding='utf-8'))
    archive=pm/'reports'/('manager-config-'+uuid.uuid4().hex+'.json')
    save(archive,{'previous':old,'replacement':config})
    save(pm/'MANAGER_CONFIG.json',config)
    data.update(bootstrapApproved=False,status='initializing')
    update(pm,data,'记录用户选择及实际 UI 模型配置，重新 bootstrap；未自动切换网页模型。')
    output(config)

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    for name in ['init','bind','begin','prepare','accept','status','blocked','handoff_prompt','developer_prompt','supervisor_review','owner_confirm','recover','replace_manager','cancel_unsent','migrate','configure']:
        q=s.add_parser(name);q.add_argument('--project',required=True)
        if name=='init': q.add_argument('--project-id',required=True);q.add_argument('--goal-file',required=True);q.add_argument('--chat-url')
        if name=='bind': q.add_argument('--chat-url',required=True)
        if name=='prepare':
            q.add_argument('--kind',choices=['bootstrap','stage','replan','final','consult'],required=True)
            q.add_argument('--summary',required=True);q.add_argument('--files',nargs='+',required=True)
        if name=='blocked':q.add_argument('--reason',required=True)
        if name=='supervisor_review':
            q.add_argument('--report',required=True);q.add_argument('--decision',choices=['approved','changes_requested'],required=True)
        if name=='owner_confirm':q.add_argument('--confirmation',required=True)
        if name in ['recover','replace_manager','cancel_unsent','migrate','configure']:
            q.add_argument('--evidence',required=True);q.add_argument('--manager-idle',action='store_true',required=True)
        if name=='cancel_unsent':
            q.add_argument('--round',required=True);q.add_argument('--reason',required=True)
        if name=='migrate':q.add_argument('--developer-idle',action='store_true',required=True)
        if name=='configure':
            q.add_argument('--policy',choices=['strict','keep_existing'],default='strict');q.add_argument('--authorization')
            for field in ['mode','model','reasoning','observed-mode','observed-model','observed-reasoning']: q.add_argument('--'+field,required=True)
        if name=='replace_manager':q.add_argument('--chat-url',required=True)
    a=p.parse_args()
    try:
        if a.action=='status': output(state(a.project)[2])
        else: globals()[a.action](a)
    except (ValueError,OSError,KeyError,TypeError) as e:
        print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=False),file=sys.stderr);sys.exit(2)
if __name__=='__main__':main()
