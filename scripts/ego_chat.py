#!/usr/bin/env python3
"""Use one existing Ego Lite task space and visible ChatGPT page for manager rounds."""
import argparse,datetime,hashlib,json,re,subprocess,sys
from pathlib import Path

STATE="""(()=>{const b=[...document.querySelectorAll('button')];const e=document.querySelector('#prompt-textarea');return JSON.stringify({url:location.href,title:document.title,busy:b.some(x=>/^(停止回答|停止生成|Stop generating|Stop response)$/i.test(x.getAttribute('aria-label')||'')||x.dataset.testid==='stop-button'),draft:e?(e.innerText||e.value||''):'',hasEditor:!!e,configurationControls:b.filter(x=>x.getClientRects().length&&!x.closest('nav,aside')&&/model|模型|GPT|Work|工作|推理|thinking/i.test((x.getAttribute('aria-label')||'')+' '+x.innerText)).slice(0,12).map(x=>({text:x.innerText.slice(0,100),aria:x.getAttribute('aria-label')}))});})()"""

def invoke(data):
    script=Path(__file__).with_suffix('.mjs').resolve()
    source=f'globalThis.PM_EGO_ARGS={json.dumps(data,ensure_ascii=False)}; await import({json.dumps(script.as_uri())})'
    result=subprocess.run(['ego-browser','nodejs','-e',source],text=True,capture_output=True,timeout=60)
    if result.returncode:raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    for line in reversed((result.stdout+'\n'+result.stderr).splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise RuntimeError('Ego returned no page result')

def js(space,page,code):
    return invoke({'action':'read','space':space,'page':page,'code':code})

def send(args):
    prompt=Path(args.prompt).read_text(encoding='utf-8')
    if len(prompt.encode())>24000:raise ValueError('Prompt too large')
    match=re.search(r'^ROUND_ID: ([A-Za-z0-9-]+)$',prompt,re.M)
    if not match:raise ValueError('Generated ROUND_ID required')
    rid=match.group(1)
    state=js(args.space,args.page,STATE)
    if not state['url'].startswith('https://chatgpt.com/'):raise ValueError('Wrong origin')
    if args.expected_url and state['url']!=args.expected_url:raise ValueError('Wrong project-manager URL')
    round_visible=js(args.space,args.page,"JSON.stringify(document.body.innerText.includes("+json.dumps(rid)+"))")
    if state['busy'] or state['draft'].strip() or round_visible or not state['hasEditor']:
        raise ValueError('Manager busy, draft present, round already visible, or composer missing')
    receipt=Path(args.receipt)
    record={'roundId':rid,'spaceId':args.space,'page':args.page,'url':state['url'],'status':'intent',
            'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'promptSha256':hashlib.sha256(prompt.encode()).hexdigest()}
    with receipt.open('x',encoding='utf-8') as file:json.dump(record,file,ensure_ascii=False,indent=2)
    try:
        outcome=invoke({'action':'send','space':args.space,'page':args.page,'prompt':str(Path(args.prompt).resolve()),'roundId':rid,'expectedUrl':args.expected_url})
        record.update(outcome)
    except Exception as error:
        record.update(status='uncertain',reason=str(error))
    receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False))
    if record['status']!='submitted':sys.exit(2)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    read=sub.add_parser('read');send_parser=sub.add_parser('send')
    for command in (read,send_parser):
        command.add_argument('--space',type=int,required=True)
        command.add_argument('--page',required=True)
    send_parser.add_argument('--prompt',required=True)
    send_parser.add_argument('--receipt',required=True)
    send_parser.add_argument('--expected-url')
    args=parser.parse_args()
    try:
        if args.action=='read':print(json.dumps(invoke({'action':'read','space':args.space,'page':args.page}),ensure_ascii=False))
        else:send(args)
    except (ValueError,RuntimeError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'ok':False,'error':str(error)},ensure_ascii=False),file=sys.stderr);sys.exit(2)

if __name__=='__main__':main()
