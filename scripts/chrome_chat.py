#!/usr/bin/env python3
"""Visible macOS Chrome bridge; no private APIs, no model changes, no scheduling."""
import argparse, datetime, hashlib, json, re, subprocess, sys, time
from pathlib import Path

def apple(script):
    r=subprocess.run(["osascript","-"],input=script,text=True,capture_output=True,timeout=30)
    if r.returncode: raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()
def js(tab, code):
    script=f'''tell application "Google Chrome"
repeat with w in windows
repeat with t in tabs of w
if (id of t as text) is "{int(tab)}" then
if URL of t does not start with "https://chatgpt.com/" then error "Wrong origin"
return execute t javascript {json.dumps(code,ensure_ascii=False)}
end if
end repeat
end repeat
error "Target tab missing"
end tell'''
    value=apple(script)
    if value=="missing value": raise RuntimeError("Chrome JavaScript returned no result; inspect permissions and tab")
    return json.loads(value)
STATE=r"""(()=>{const b=[...document.querySelectorAll('button')];const editor=document.querySelector('#prompt-textarea');
return JSON.stringify({url:location.href,title:document.title,busy:b.some(e=>/^(停止回答|停止生成|Stop generating|Stop response)$/i.test(e.getAttribute('aria-label')||'')||e.dataset.testid==='stop-button'),draft:editor?(editor.innerText||editor.value||''):'',headerText:[...document.querySelectorAll('header')].map(e=>e.innerText).join('\n'),configurationControls:b.filter(e=>e.getClientRects().length&&!e.closest('nav,aside')&&!/^(置顶 |打开“)/.test(e.getAttribute('aria-label')||'')&&/model|模型|GPT|Work|工作|推理|thinking/i.test((e.getAttribute('aria-label')||'')+' '+(e.dataset.testid||'')+' '+e.innerText)).slice(0,30).map(e=>({text:e.innerText.slice(0,120),aria:e.getAttribute('aria-label'),testid:e.dataset.testid})),text:document.body.innerText.slice(-16000),buttons:b.slice(-30).map(e=>({text:e.innerText,aria:e.getAttribute('aria-label'),testid:e.dataset.testid})),hasEditor:!!editor});})()"""
def listing():
    return apple('''tell application "Google Chrome"
set resultText to ""
repeat with w in windows
repeat with t in tabs of w
if URL of t starts with "https://chatgpt.com/" then
set resultText to resultText & (id of w as text) & " | " & (id of t as text) & " | " & (title of t) & " | " & (URL of t) & linefeed
end if
end repeat
end repeat
return resultText
end tell''')
def focus(tab):
    return apple(f'''tell application "Google Chrome"
repeat with w in windows
repeat with i from 1 to count of tabs of w
if (id of tab i of w as text) is "{int(tab)}" then
if URL of tab i of w does not start with "https://chatgpt.com/" then error "Wrong origin"
set active tab index of w to i
set index of w to 1
activate
return "Target ChatGPT tab visible"
end if
end repeat
end repeat
error "Target tab missing"
end tell''')

def settled_draft(tab,text,initial):
    normalize=lambda value: re.sub(r"\n+", "\n", value.strip())
    candidate=initial
    for attempt in range(5):
        if normalize(candidate)==normalize(text):return
        if attempt==4:break
        time.sleep(0.25)
        state=js(tab,STATE)
        if state.get('busy'):raise RuntimeError('Composer became busy; do not submit')
        candidate=state.get('draft','')
    raise RuntimeError('Composer text mismatch')

def send(a):
    text=Path(a.prompt).read_text(encoding="utf-8")
    if len(text.encode())>24000: raise ValueError("Prompt too large")
    m=re.search(r"^ROUND_ID: ([A-Za-z0-9-]+)$",text,re.M)
    if not m: raise ValueError("Generated ROUND_ID required")
    rid=m.group(1)
    state=js(a.tab,STATE)
    if getattr(a,"expected_url",None) and state["url"]!=a.expected_url: raise ValueError("Wrong project-manager URL; refusing cross-project send")
    if state["busy"]: raise ValueError("BUSY: do not interrupt; inspect next time")
    if rid in state["text"]: raise ValueError("Round already visible; do not resend")
    if state["draft"].strip(): raise ValueError("Existing draft; refusing overwrite")
    if not state["hasEditor"]: raise ValueError("No composer")
    receipt=Path(a.receipt)
    record={"roundId":rid,"tabId":a.tab,"url":state["url"],"status":"intent",
            "createdAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "promptSha256":hashlib.sha256(text.encode()).hexdigest()}
    with receipt.open("x") as h: json.dump(record,h,ensure_ascii=False,indent=2)
    try:
        inserted=js(a.tab,"""(()=>{const e=document.querySelector('#prompt-textarea');e.focus();
document.execCommand('insertText',false,TEXT);
e.dispatchEvent(new Event('input',{bubbles:true}));
return JSON.stringify({draft:e.innerText||e.value||''});})()""".replace("TEXT",json.dumps(text,ensure_ascii=False),1))
        settled_draft(a.tab,text,inserted["draft"])
        result=js(a.tab,r"""(()=>{const all=[...document.querySelectorAll('button')];
if(all.some(e=>/^(停止回答|停止生成|Stop generating|Stop response)$/i.test(e.getAttribute('aria-label')||'')))return JSON.stringify({sent:false,reason:'busy'});
const candidates=all.filter(e=>!e.disabled&&(e.dataset.testid==='send-button'||/^(发送提示词|发送消息|Send prompt|Send message)$/i.test(e.getAttribute('aria-label')||'')));
if(candidates.length!==1)return JSON.stringify({sent:false,reason:'ambiguous send button'});
candidates[0].click();return JSON.stringify({sent:true});})()""")
        if not result.get("sent"): raise RuntimeError(str(result))
        for _ in range(8):
            time.sleep(1)
            seen=js(a.tab,STATE)
            # Verify round in user message, not merely in draft.
            confirmed=js(a.tab,"JSON.stringify([...document.querySelectorAll('[data-message-author-role=\"user\"]')].some(e=>e.innerText.includes("+json.dumps(rid)+")))")
            if confirmed:
                record.update(status="submitted",url=seen["url"],busy=seen["busy"]); break
        else: record.update(status="uncertain",reason="No user-message receipt; inspect before retry")
    except Exception as e:
        record.update(status="uncertain",reason=str(e))
    receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
    print(json.dumps(record,ensure_ascii=False))
    if record["status"]!="submitted": sys.exit(2)
def main():
    sys.stdout.reconfigure(errors="backslashreplace")
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="action",required=True)
    sub.add_parser("list");sub.add_parser("new")
    f=sub.add_parser("focus");f.add_argument("--tab",type=int,required=True)
    r=sub.add_parser("read");r.add_argument("--tab",type=int,required=True)
    s=sub.add_parser("send");s.add_argument("--tab",type=int,required=True);s.add_argument("--prompt",required=True);s.add_argument("--receipt",required=True);s.add_argument("--expected-url")
    a=p.parse_args()
    try:
        if a.action=="list": print(listing())
        elif a.action=="focus": print(focus(a.tab))
        elif a.action=="new":
            print(apple('''tell application "Google Chrome"
if (count of windows) is 0 then make new window
set w to front window
set t to make new tab at end of tabs of w with properties {URL:"https://chatgpt.com/"}
return "{\\"windowId\\":" & (id of w as text) & ",\\"tabId\\":" & (id of t as text) & "}"
end tell'''))
        elif a.action=="read": print(json.dumps(js(a.tab,STATE),ensure_ascii=False))
        else: send(a)
    except Exception as e:
        print(json.dumps({"ok":False,"error":str(e)},ensure_ascii=False),file=sys.stderr);sys.exit(2)
if __name__=="__main__":main()
