"""Behavior tests use isolated temporary projects; never forge live PM output."""
import argparse
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

h = load('handoff')
b = load('chrome_chat')

class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root/'src').mkdir()
        (self.root/'src/a.txt').write_text('version 1', encoding="utf-8")
        (self.root/'summary.md').write_text('Synthetic isolated test only', encoding="utf-8")
        args = argparse.Namespace(project=str(self.root),project_id='test-only',summary=str(self.root/'summary.md'),files=['src'],probe=True)
        with contextlib.redirect_stdout(io.StringIO()): h.prepare(args)
        self.round = next((self.root/'.gpt-pm/rounds').iterdir())
        self.req = json.loads((self.round/'REQUEST.json').read_text(encoding="utf-8"))

    def outputs(self):
        out = self.round/'outbox'
        for name in ['REVIEW.md','NEXT_TASK.md','ACCEPTANCE.md']:
            (out/name).write_text('Isolated synthetic fixture', encoding="utf-8")
        (out/'WEB_GPT_PROBE.txt').write_text(self.req['probeNonce']+'\n', encoding="utf-8")
        h.dump(out/'DONE.json', dict(schemaVersion=1,roundId=self.req['roundId'],snapshotSha256=self.req['snapshotSha256'],producer='web-gpt-via-webcodex',verifiedAt=h.now(),testsRun=[],status='approved',probeNonce=self.req['probeNonce']))

    def verify(self):
        with contextlib.redirect_stdout(io.StringIO()): h.verify(argparse.Namespace(round=str(self.round)))

    def test_complete_round(self):
        self.outputs()
        self.verify()

    def test_partial_output_rejected(self):
        with self.assertRaisesRegex(ValueError,'Missing'): self.verify()

    def test_changed_and_added_source_rejected(self):
        self.outputs()
        (self.root/'src/a.txt').write_text('version 2', encoding="utf-8")
        with self.assertRaisesRegex(ValueError,'STALE'): self.verify()
        (self.root/'src/a.txt').write_text('version 1', encoding="utf-8")
        (self.root/'src/new.txt').write_text('new file', encoding="utf-8")
        with self.assertRaisesRegex(ValueError,'STALE'): self.verify()

    def test_wrong_round_rejected(self):
        self.outputs()
        p=self.round/'outbox/DONE.json'
        data=json.loads(p.read_text(encoding="utf-8")); data['roundId']='wrong'; h.dump(p,data)
        with self.assertRaisesRegex(ValueError,'roundId'): self.verify()

    def test_stale_blocked_delivery_verified_but_not_actionable(self):
        self.outputs()
        p=self.round/'outbox/DONE.json'
        data=json.loads(p.read_text(encoding="utf-8")); data['status']='blocked'; h.dump(p,data)
        (self.root/'src/a.txt').write_text('concurrent edit', encoding="utf-8")
        output=io.StringIO()
        with contextlib.redirect_stdout(output): h.verify(argparse.Namespace(round=str(self.round)))
        result=json.loads(output.getvalue())
        self.assertTrue(result['deliveryVerified'])
        self.assertFalse(result['sourceUnchanged'])
        self.assertFalse(result['actionable'])
        self.assertEqual(result['changedFiles'],['src/a.txt'])

    def test_stale_blocked_does_not_skip_probe_check(self):
        self.outputs()
        p=self.round/'outbox/DONE.json'
        data=json.loads(p.read_text(encoding="utf-8")); data['status']='blocked'; h.dump(p,data)
        (self.root/'src/a.txt').write_text('concurrent edit', encoding="utf-8")
        (self.round/'outbox/WEB_GPT_PROBE.txt').write_text('wrong', encoding="utf-8")
        with self.assertRaisesRegex(ValueError,'Probe'): self.verify()

    def test_wrong_probe_rejected(self):
        self.outputs()
        (self.round/'outbox/WEB_GPT_PROBE.txt').write_text('wrong', encoding="utf-8")
        with self.assertRaisesRegex(ValueError,'Probe'): self.verify()

    def test_sensitive_and_traversal_paths_rejected(self):
        for name in ['../x','.env','.env.production','private.key']:
            with self.assertRaises(ValueError): h.fingerprint(self.root,[name])

    def test_symlink_rejected(self):
        (self.root/'link').symlink_to(self.root/'src')
        with self.assertRaisesRegex(ValueError,'Symlink'): h.fingerprint(self.root,['link'])

    def test_transient_composer_settles_without_reinserting(self):
        with patch.object(b,'js',return_value={'draft':'expected\n\ntext','busy':False}) as js,patch.object(b.time,'sleep'):
            b.settled_draft(1,'expected\ntext','partial')
            self.assertEqual(js.call_count,1)

    def test_real_composer_change_still_rejected(self):
        with patch.object(b,'js',return_value={'draft':'different content','busy':False}),patch.object(b.time,'sleep'):
            with self.assertRaisesRegex(RuntimeError,'mismatch'):b.settled_draft(1,'expected','different content')

    def test_busy_draft_duplicate_never_submit(self):
        args=argparse.Namespace(tab=1,prompt=str(self.round/'PROMPT.txt'),receipt=str(self.round/'receipt.json'))
        for state in [dict(busy=True,text='',draft='',hasEditor=True),dict(busy=False,text='',draft='user draft',hasEditor=True),dict(busy=False,text=self.req['roundId'],draft='',hasEditor=True)]:
            with patch.object(b,'js',return_value=state) as js:
                with self.assertRaises(ValueError): b.send(args)
                self.assertEqual(js.call_count,1)
                self.assertFalse(Path(args.receipt).exists())

if __name__ == '__main__': unittest.main()
