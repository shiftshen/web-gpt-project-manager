"""Prompt release gates and diagnostic-only rounds."""
import json, unittest
from pathlib import Path
import project as p
import test_project as fixtures

class DeliveryTests(unittest.TestCase):
    setUp=fixtures.ProjectTests.setUp
    call=fixtures.ProjectTests.call
    prepare=fixtures.ProjectTests.prepare
    pm=fixtures.ProjectTests.pm
    bootstrap=fixtures.ProjectTests.bootstrap

    def unknown_config(self,**extra):
        args=dict(manager_idle=True,evidence=str(self.report),mode='Work',model='GPT-6',reasoning='default',observed_mode='unknown',observed_model='unknown',observed_reasoning='unknown')
        args.update(extra);return self.call(p.configure,**args)

    def test_handoff_available_but_goal_gated(self):
        info=self.call(p.handoff_prompt)
        self.assertFalse(info['goalReleased']);self.assertTrue(Path(info['handoffPrompt']).exists())
        with self.assertRaisesRegex(ValueError,'bootstrap'):self.call(p.developer_prompt)
        self.assertFalse((self.root/'.gpt-pm/DEVELOPER_GOAL_PROMPT.md').exists())

    def test_after_handshake_two_prompts_bind_same_project(self):
        self.bootstrap();info=self.call(p.developer_prompt)
        self.assertTrue(info['goalReleased'])
        for key in ['handoffPrompt','goalPrompt','developerPrompt']:
            text=Path(info[key]).read_text(encoding='utf-8')
            self.assertIn(str(self.root),text);self.assertIn('https://chatgpt.com/c/pm-a',text);self.assertNotIn('{{',text)
        self.prepare('stage')
        with self.assertRaises(ValueError):self.call(p.developer_prompt)

    def test_unknown_can_consult_but_does_not_release_development(self):
        self.unknown_config();old=(self.root/'.gpt-pm/PLAN.md').read_bytes()
        folder=self.prepare('consult');self.pm(folder)
        result=self.call(p.accept)
        self.assertTrue(result['consultOnly']);self.assertFalse(result['state']['bootstrapApproved'])
        self.assertEqual(result['state']['status'],'initializing')
        self.assertEqual((self.root/'.gpt-pm/PLAN.md').read_bytes(),old)
        with self.assertRaises(ValueError):self.call(p.begin)
        with self.assertRaises(ValueError):self.prepare('bootstrap')

    def test_keep_existing_requires_authorization_preserves_unknown(self):
        with self.assertRaisesRegex(ValueError,'authorization'):self.unknown_config(policy='keep_existing')
        self.unknown_config(policy='keep_existing',authorization=str(self.report))
        folder=self.prepare('bootstrap');self.pm(folder);self.call(p.accept)
        config=json.loads((self.root/'.gpt-pm/MANAGER_CONFIG.json').read_text())
        self.assertEqual(config['observed']['model'],'unknown')
        self.assertFalse(config['allowAutomaticUpgrade'])
        self.assertEqual(self.call(p.begin)['status'],'running')

if __name__=='__main__':unittest.main()
