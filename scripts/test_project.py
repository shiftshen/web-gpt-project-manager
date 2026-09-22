"""Lifecycle tests use temporary projects and synthetic PM fixtures only."""
import argparse, contextlib, io, json, tempfile, unittest
from pathlib import Path
import project as p

class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve()
        self.root=self.base/'project-a';self.root.mkdir()
        (self.root/'src').mkdir();(self.root/'src/code.txt').write_text('initial', encoding="utf-8")
        self.goal=self.base/'goal.md';self.goal.write_text('Implement the requested behavior and verify it. No publishing.', encoding="utf-8")
        self.report=self.root/'report.md';self.report.write_text('Synthetic test report', encoding="utf-8")
        self.call(p.init,project=str(self.root),project_id='project-a',goal_file=str(self.goal),chat_url='https://chatgpt.com/c/pm-a')

    def call(self,fn,**kw):
        kw.setdefault('project',str(self.root))
        capture=io.StringIO()
        with contextlib.redirect_stdout(capture): fn(argparse.Namespace(**kw))
        return json.loads(capture.getvalue()) if capture.getvalue() else None

    def prepare(self,kind='bootstrap'):
        result=self.call(p.prepare,kind=kind,summary=str(self.report),files=['src'])
        return Path(result['round'])

    def pm(self,folder,status='approved',complete=None):
        req=json.loads((folder/'REQUEST.json').read_text(encoding="utf-8"))
        out=folder/'outbox'
        for name in ['REVIEW.md','NEXT_TASK.md','ACCEPTANCE.md']:(out/name).write_text('Synthetic '+status+' evidence', encoding="utf-8")
        done={'schemaVersion':1,'roundId':req['roundId'],'status':status,'snapshotSha256':req['snapshotSha256'],'producer':'web-gpt-via-webcodex','verifiedAt':p.h.now(),'testsRun':[]}
        if req['probeNonce']:
            (out/'WEB_GPT_PROBE.txt').write_text(req['probeNonce']+'\n', encoding="utf-8");done['probeNonce']=req['probeNonce']
        if complete is not None:done['goalComplete']=complete
        p.save(out/'DONE.json',done)

    def bootstrap(self):
        folder=self.prepare();self.pm(folder);return self.call(p.accept)

    def test_gate_before_handshake(self):
        with self.assertRaisesRegex(ValueError,'GATE_CLOSED'):self.call(p.begin)
        with self.assertRaisesRegex(ValueError,'GATE_CLOSED'):self.prepare('stage')

    def test_lifecycle_fixed_chat_and_final(self):
        result=self.bootstrap();self.assertTrue(result['state']['bootstrapApproved'])
        self.assertEqual(result['state']['status'],'ready')
        self.call(p.begin);folder=self.prepare('stage');self.pm(folder)
        result=self.call(p.accept);self.assertEqual(result['state']['status'],'ready')
        self.assertEqual(result['state']['chatUrl'],'https://chatgpt.com/c/pm-a')
        folder=self.prepare('final');self.pm(folder,complete=True)
        self.assertEqual(self.call(p.accept)['state']['status'],'supervisor_review_pending')
        with self.assertRaises(ValueError):self.call(p.begin)
        report=self.base/'supervisor.md';report.write_text('Independent checks passed on actual final snapshot', encoding="utf-8")
        result=self.call(p.supervisor_review,report=str(report),decision='approved')
        self.assertEqual(result['status'],'owner_acceptance_pending')
        confirm=self.base/'owner.md';confirm.write_text('Synthetic explicit owner acceptance fixture', encoding="utf-8")
        self.assertEqual(self.call(p.owner_confirm,confirmation=str(confirm))['status'],'complete')

    def test_incomplete_handshake_keeps_gate_closed(self):
        folder=self.prepare();self.pm(folder);(folder/'outbox/WEB_GPT_PROBE.txt').unlink()
        with self.assertRaises(OSError):self.call(p.accept)
        self.assertFalse(p.state(str(self.root))[2]['bootstrapApproved'])

    def test_pending_round_cannot_duplicate(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError,'Pending'):self.prepare()

    def test_final_requires_explicit_completion(self):
        self.bootstrap();folder=self.prepare('final');self.pm(folder)
        with self.assertRaisesRegex(ValueError,'goalComplete'):self.call(p.accept)
        self.assertNotEqual(p.state(str(self.root))[2]['status'],'complete')

    def test_shared_goal_mutation_rejected(self):
        folder=self.prepare();self.pm(folder)
        (self.root/'.gpt-pm/GOAL.md').write_text('Different goal', encoding="utf-8")
        with self.assertRaisesRegex(ValueError,'Shared goal'):self.call(p.accept)

    def test_changes_requested_reworks_same_stage(self):
        self.bootstrap();self.call(p.begin);folder=self.prepare('stage');self.pm(folder,'changes_requested')
        self.assertEqual(self.call(p.accept)['state']['status'],'changes_requested')
        self.assertEqual(self.call(p.begin)['stage'],1)

    def test_project_isolation_and_wrong_chat(self):
        other=self.base/'project-b';other.mkdir()
        b=self.call(p.init,project=str(other),project_id='project-b',goal_file=str(self.goal),chat_url='https://chatgpt.com/c/pm-b')
        self.assertEqual(b['chatUrl'],'https://chatgpt.com/c/pm-b')
        with self.assertRaisesRegex(ValueError,'Different PM'):self.call(p.bind,chat_url='https://chatgpt.com/c/pm-b')
        self.assertEqual(p.state(str(self.root))[2]['chatUrl'],'https://chatgpt.com/c/pm-a')

    def test_idempotent_init_preserves_state(self):
        self.bootstrap()
        data=self.call(p.init,project_id='project-a',goal_file=str(self.goal),chat_url='https://chatgpt.com/c/pm-a')
        self.assertTrue(data['bootstrapApproved'])
        self.goal.write_text('Different user goal', encoding="utf-8")
        with self.assertRaises(ValueError):self.call(p.init,project_id='project-a',goal_file=str(self.goal),chat_url=None)

    def test_stale_blocked_is_received_without_approval(self):
        folder=self.prepare();self.pm(folder,'blocked')
        (self.root/'src/code.txt').write_text('concurrent edit', encoding="utf-8")
        result=self.call(p.accept)
        self.assertFalse(result['state']['bootstrapApproved'])
        self.assertEqual(result['state']['status'],'blocked')
        self.assertFalse(result['review']['actionable'])

    def test_developer_prompt_requires_bootstrap_and_is_project_specific(self):
        with self.assertRaisesRegex(ValueError,'bootstrap'):self.call(p.developer_prompt)
        self.bootstrap()
        result=self.call(p.developer_prompt)
        content=Path(result['developerPrompt']).read_text(encoding="utf-8")
        self.assertIn(str(self.root),content)
        self.assertIn('https://chatgpt.com/c/pm-a',content)
        self.assertNotIn('{{',content)

    def test_owner_cannot_close_before_supervisor(self):
        self.bootstrap();folder=self.prepare('final');self.pm(folder,complete=True);self.call(p.accept)
        confirm=self.base/'owner.md';confirm.write_text('Synthetic acceptance', encoding="utf-8")
        with self.assertRaisesRegex(ValueError,'supervisor approval'):self.call(p.owner_confirm,confirmation=str(confirm))

    def test_final_source_change_blocks_supervisor_approval(self):
        self.bootstrap();folder=self.prepare('final');self.pm(folder,complete=True);self.call(p.accept)
        (self.root/'src/code.txt').write_text('changed after review', encoding="utf-8")
        report=self.base/'review.md';report.write_text('Evidence', encoding="utf-8")
        with self.assertRaisesRegex(ValueError,'STALE'):self.call(p.supervisor_review,report=str(report),decision='approved')
        self.assertEqual(self.call(p.supervisor_review,report=str(report),decision='changes_requested')['status'],'changes_requested')

    def test_repeated_rework_escalates(self):
        self.bootstrap();self.call(p.begin)
        for attempt in range(2):
            folder=self.prepare('stage');self.pm(folder,'changes_requested');result=self.call(p.accept)
            if attempt==0:self.call(p.begin)
        self.assertEqual(result['state']['status'],'escalated')
        with self.assertRaises(ValueError):self.call(p.begin)



class RecoveryTests(unittest.TestCase):
    setUp = ProjectTests.setUp
    call = ProjectTests.call
    prepare = ProjectTests.prepare
    pm = ProjectTests.pm
    bootstrap = ProjectTests.bootstrap
    def test_replan_updates_revision_without_changing_goal(self):
        self.bootstrap();self.call(p.begin)
        goal=(self.root/'.gpt-pm/GOAL.md').read_bytes()
        folder=self.prepare('replan');self.pm(folder)
        result=self.call(p.accept)
        self.assertEqual(result['state']['planRevision'],2)
        self.assertEqual((self.root/'.gpt-pm/GOAL.md').read_bytes(),goal)

    def test_recover_preserves_incomplete_round_and_closed_gate(self):
        folder=self.prepare()
        evidence=self.base/'recovery.md';evidence.write_text('Synthetic: confirmed manager stopped; transport restored',encoding='utf-8')
        with self.assertRaises(ValueError):self.call(p.recover,evidence=str(evidence),manager_idle=False)
        result=self.call(p.recover,evidence=str(evidence),manager_idle=True)
        self.assertEqual(result['status'],'initializing')
        self.assertTrue(folder.exists())
        self.assertFalse(result['bootstrapApproved'])

    def test_manager_replacement_requires_new_handshake(self):
        self.bootstrap()
        evidence=self.base/'handover.md';evidence.write_text('Synthetic supervisor migration authorization',encoding='utf-8')
        result=self.call(p.replace_manager,manager_idle=True,evidence=str(evidence),chat_url='https://chatgpt.com/c/pm-new')
        self.assertFalse(result['bootstrapApproved'])
        with self.assertRaises(ValueError):self.call(p.begin)

if __name__=='__main__':unittest.main()
