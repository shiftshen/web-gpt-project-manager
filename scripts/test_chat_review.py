"""Visible-chat capture/accept fixtures; no real manager outputs are fabricated."""
import contextlib,io,json,unittest
from pathlib import Path
from unittest.mock import patch
import project as p
import chat_review as chat
import test_project as fixtures

class ChatTests(unittest.TestCase):
    setUp=fixtures.ProjectTests.setUp
    call=fixtures.ProjectTests.call
    prepare=fixtures.ProjectTests.prepare
    pm=fixtures.ProjectTests.pm
    bootstrap=fixtures.ProjectTests.bootstrap

    def chat_round(self,kind='stage'):
        return Path(self.call(p.prepare,kind=kind,summary=str(self.report),files=['src'],transport='chat')['round'])

    def capture(self,folder,**changes):
        req=json.loads((folder/'REQUEST.json').read_text())
        d={'roundId':folder.name,'status':'approved','reason':'fixture review','nextTask':'bounded implementation','acceptance':'verify expected result'};d.update(changes)
        messages=[{'role':'user','text':(folder/'PROMPT.txt').read_text(encoding='utf-8')},{'role':'assistant','text':'```json\n'+json.dumps(d)+'\n```'}]
        with patch('chrome_chat.js',side_effect=[{'url':req['chatUrl'],'busy':False},messages]),contextlib.redirect_stdout(io.StringIO()):chat.capture(1,folder)

    def test_browser_rendered_code_blocks_and_inline_code_are_accepted(self):
        self.bootstrap();folder=self.chat_round()
        req=json.loads((folder/'REQUEST.json').read_text())
        d={'roundId':folder.name,'status':'approved','reason':'fixture','nextTask':'next','acceptance':'check'}
        original=(folder/'PROMPT.txt').read_text(encoding='utf-8')+'\nVerify `6/6` in ```text\nreport\n```'
        (folder/'PROMPT.txt').write_text(original,encoding='utf-8')
        messages=[{'role':'user','text':original.replace('`','')+' 展开'},
                  {'role':'assistant','text':'JSON\n'+json.dumps(d)}]
        with patch('chrome_chat.js',side_effect=[{'url':req['chatUrl'],'busy':False},messages]),contextlib.redirect_stdout(io.StringIO()):chat.capture(1,folder)
        self.assertEqual(self.call(p.accept)['state']['status'],'ready')

    def test_brief_preserves_full_report_but_sends_only_summary(self):
        self.bootstrap()
        self.report.write_text('Long evidence '*700,encoding='utf-8')
        brief=self.base/'brief.md';brief.write_text('Short manager question',encoding='utf-8')
        result=self.call(p.prepare,kind='stage',summary=str(self.report),brief=str(brief),files=['src'],transport='chat')
        folder=Path(result['round'])
        self.assertIn('Short manager question',(folder/'PROMPT.txt').read_text(encoding='utf-8'))
        self.assertNotIn('Long evidence',(folder/'PROMPT.txt').read_text(encoding='utf-8'))
        self.assertEqual((folder/'HANDOFF.md').read_bytes(),self.report.read_bytes())

    def test_chat_accept_without_pm_writing_any_files(self):
        self.bootstrap();folder=self.chat_round();self.capture(folder)
        self.assertEqual(list((folder/'outbox').iterdir()),[])
        result=self.call(p.accept)
        self.assertEqual(result['state']['status'],'ready')
        self.assertEqual(result['review']['producer'],'web-gpt-chat')
        self.assertTrue((folder/'CHAT_ACCEPTED.json').exists())
        self.assertIn('bounded implementation',(self.root/'.gpt-pm/PLAN.md').read_text(encoding='utf-8'))

    def test_captured_chat_cannot_be_cancelled_as_unsent(self):
        self.bootstrap();folder=self.chat_round();self.capture(folder)
        with self.assertRaisesRegex(ValueError,'output'):
            self.call(p.cancel_unsent,round=folder.name,reason='fixture',manager_idle=True,evidence=str(self.report))

    def test_chat_cannot_replace_bootstrap(self):
        with self.assertRaisesRegex(ValueError,'probe'):self.chat_round('bootstrap')

    def test_wrong_chat_or_busy_not_captured(self):
        self.bootstrap();folder=self.chat_round()
        for state in [{'url':'https://chatgpt.com/c/wrong','busy':False},{'url':'https://chatgpt.com/c/pm-a','busy':True}]:
            with patch('chrome_chat.js',return_value=state),self.assertRaises(ValueError):chat.capture(1,folder)
        self.assertFalse((folder/'CHAT_REPLY.json').exists())

    def test_stale_chat_approval_rejected(self):
        self.bootstrap();folder=self.chat_round();self.capture(folder)
        (self.root/'src/code.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'STALE'):self.call(p.accept)

    def test_no_decision_requires_followup_not_local_invention(self):
        self.bootstrap();folder=self.chat_round();req=json.loads((folder/'REQUEST.json').read_text())
        with self.assertRaisesRegex(ValueError,'explicit'):chat.parse_reply('Looks good',req)

    def test_final_and_tamper_detection(self):
        self.bootstrap();folder=self.chat_round('final');self.capture(folder,goalComplete=True)
        result=self.call(p.accept);self.assertEqual(result['state']['status'],'supervisor_review_pending')
        p.final_fresh(self.root/'.gpt-pm',result['state'])
        capture=json.loads((folder/'CHAT_REPLY.json').read_text());capture['messages'][-1]['text']=capture['messages'][-1]['text'].replace('fixture review','altered review')
        p.save(folder/'CHAT_REPLY.json',capture)
        with self.assertRaisesRegex(ValueError,'changed'):p.final_fresh(self.root/'.gpt-pm',result['state'])

    def test_unrelated_user_followup_rejected(self):
        self.bootstrap();folder=self.chat_round();self.capture(folder)
        record=json.loads((folder/'CHAT_REPLY.json').read_text());record['messages'].insert(1,{'role':'user','text':'different project'})
        p.save(folder/'CHAT_REPLY.json',record)
        with self.assertRaisesRegex(ValueError,'Unrelated'):self.call(p.accept)

if __name__=='__main__':unittest.main()
