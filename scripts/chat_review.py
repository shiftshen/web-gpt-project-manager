"""Capture visible manager decisions; local records are not PM-written outbox files."""
import argparse,json,re,sys
from pathlib import Path
import handoff as h


def visible_prompt(text):
    # Chrome renders Markdown code delimiters; preserve all substantive characters.
    return re.sub(r'\s+',' ',re.sub(r'`+','',text)).strip()

def parse_reply(text,req):
    blocks=re.findall(r'```(?:json)?\s*(\{.*?\})\s*```',text,re.S)
    if not blocks: blocks=[re.sub(r'^(?:JSON|json)\s*\n','',text.strip())]
    decisions=[]
    for block in blocks:
        try: obj=json.loads(block)
        except json.JSONDecodeError:continue
        if isinstance(obj,dict) and obj.get('roundId')==req['roundId']:decisions.append(obj)
    if len(decisions)!=1:raise ValueError('Need one explicit manager decision for this round; first inspect visible tab/overlay and wait, then ask a brief follow-up if genuinely missing')
    d=decisions[0]
    if d.get('status') not in ['approved','changes_requested','blocked']:raise ValueError('Invalid manager decision')
    for key in ['reason','nextTask','acceptance']:
        if not isinstance(d.get(key),str) or not d[key].strip():raise ValueError('Missing manager field: '+key)
    if req['kind']=='final' and d['status']=='approved' and d.get('goalComplete') is not True:raise ValueError('Final requires goalComplete=true')
    return d


def capture(tab,folder):
    import chrome_chat as browser
    folder=Path(folder).resolve(strict=True)
    req=json.loads((folder/'REQUEST.json').read_text(encoding='utf-8'))
    if req.get('transport')!='chat':raise ValueError('Not a chat decision round')
    state=browser.js(tab,browser.STATE)
    if state['url']!=req['chatUrl']:raise ValueError('Wrong manager URL')
    if state['busy']:raise ValueError('Manager still responding; wait before capturing')
    messages=browser.js(tab,"JSON.stringify([...document.querySelectorAll('[data-message-author-role]')].map(e=>({role:e.dataset.messageAuthorRole,text:e.innerText})))")
    marker='ROUND_ID: '+req['roundId']
    starts=[i for i,m in enumerate(messages) if m['role']=='user' and marker in m['text']]
    if len(starts)!=1:raise ValueError('Missing/duplicate original round in visible conversation; inspect before capture')
    chain=messages[starts[0]:]
    expected=visible_prompt((folder/'PROMPT.txt').read_text(encoding='utf-8'))
    if expected not in visible_prompt(chain[0]['text']):raise ValueError('Visible request does not match prepared prompt')
    for m in chain[1:]:
        if m['role']=='user' and ('FOLLOWUP_FOR: '+req['roundId']) not in m['text']:
            raise ValueError('Unrelated later user message; inspect correct conversation turn')
    if not chain or chain[-1]['role']!='assistant':raise ValueError('No completed manager reply')
    parse_reply(chain[-1]['text'],req)
    record={'schemaVersion':1,'producer':'visible-chrome-transcript','url':state['url'],
            'roundId':req['roundId'],'capturedAt':h.now(),'requestSha256':h.sha((folder/'REQUEST.json').read_bytes()),'messages':chain}
    target=folder/'CHAT_REPLY.json'
    with target.open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
    print(json.dumps({'captured':str(target),'status':'captured_not_accepted'}))


def verify(folder):
    folder=Path(folder)
    for name in ['CHAT_REPLY.json','REQUEST.json','SNAPSHOT.json','HANDOFF.md']:
        if (folder/name).is_symlink():raise ValueError('Symlink not allowed in chat evidence')
    req=json.loads((folder/'REQUEST.json').read_text(encoding='utf-8'))
    raw=(folder/'CHAT_REPLY.json').read_bytes();record=json.loads(raw)
    if record.get('producer')!='visible-chrome-transcript' or record.get('url')!=req['chatUrl'] or record.get('roundId')!=req['roundId']:
        raise ValueError('Wrong conversation/round/provenance')
    if record.get('requestSha256')!=h.sha((folder/'REQUEST.json').read_bytes()):raise ValueError('Request changed after capture')
    if h.sha((folder/'SNAPSHOT.json').read_bytes())!=req['snapshotSha256'] or h.sha((folder/'HANDOFF.md').read_bytes())!=req['handoffSha256']:
        raise ValueError('Snapshot or handoff changed')
    messages=record['messages']
    expected=visible_prompt((folder/'PROMPT.txt').read_text(encoding='utf-8'))
    if not messages or expected not in visible_prompt(messages[0]['text']):raise ValueError('Captured request does not match prepared prompt')
    if not messages or messages[0]['role']!='user' or ('ROUND_ID: '+req['roundId']) not in messages[0]['text'] or messages[-1]['role']!='assistant':raise ValueError('Invalid conversation chain')
    for m in messages[1:]:
        if m['role']=='user' and ('FOLLOWUP_FOR: '+req['roundId']) not in m['text']:raise ValueError('Unrelated followup')
    d=parse_reply(messages[-1]['text'],req)
    snap=json.loads((folder/'SNAPSHOT.json').read_text(encoding='utf-8'))
    current=h.fingerprint(Path(snap['projectRoot']),snap['selections']);fresh=current==snap['files']
    if not fresh and d['status']!='blocked':raise ValueError('STALE: source changed since manager request')
    marker=folder/'CHAT_ACCEPTED.json'
    if marker.is_symlink():raise ValueError('Symlink not allowed in accepted chat evidence')
    if marker.exists():
        accepted=json.loads(marker.read_text(encoding='utf-8'))
        if accepted['replySha256']!=h.sha(raw):raise ValueError('Accepted chat evidence changed')
    return {'verified':True,'deliveryVerified':True,'status':d['status'],'sourceUnchanged':fresh,
            'actionable':fresh and d['status']=='approved','probeVerified':False,'roundId':req['roundId'],
            'producer':'web-gpt-chat','decision':d,'replySha256':h.sha(raw)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tab',type=int,required=True);p.add_argument('--round',required=True);a=p.parse_args()
    try:capture(a.tab,a.round)
    except (ValueError,OSError,KeyError,TypeError,RuntimeError) as e:print(str(e),file=sys.stderr);sys.exit(2)
if __name__=='__main__':main()
