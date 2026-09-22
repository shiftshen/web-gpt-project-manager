"""Auditable transitions on isolated legacy state; no browser claims."""
import json, unittest
import project as p
import test_project as fixtures

class MigrationTests(unittest.TestCase):
    setUp=fixtures.ProjectTests.setUp
    call=fixtures.ProjectTests.call
    prepare=fixtures.ProjectTests.prepare
    pm=fixtures.ProjectTests.pm
    bootstrap=fixtures.ProjectTests.bootstrap

    def legacy(self,version=2):
        _,pm,data=p.state(str(self.root));data['schemaVersion']=version
        p.save(pm/'PROJECT.json',data)
        return pm,data

    def migrate(self,**extra):
        args=dict(manager_idle=True,developer_idle=True,evidence=str(self.report));args.update(extra)
        return self.call(p.migrate,**args)

    def cancel(self,folder):
        return self.call(p.cancel_unsent,round=folder.name,reason='Superseded unsent fixture',manager_idle=True,evidence=str(self.report))

    def test_cancel_unsent_preserves_originals(self):
        folder=self.prepare();before=(folder/'REQUEST.json').read_bytes()
        self.assertIsNone(self.cancel(folder)['activeRound'])
        self.assertEqual((folder/'REQUEST.json').read_bytes(),before)
        self.assertFalse(json.loads((folder/'CANCELLED.json').read_text())['approved'])
        with self.assertRaisesRegex(ValueError,'already cancelled'):self.cancel(folder)

    def test_cancel_refuses_uncertain_and_output(self):
        folder=self.prepare();p.save(folder/'browser-receipt.json',{'status':'uncertain'})
        with self.assertRaisesRegex(ValueError,'receipt'):self.cancel(folder)
        (folder/'browser-receipt.json').unlink() # fixture only
        (folder/'outbox/REVIEW.md').write_text('partial')
        with self.assertRaisesRegex(ValueError,'output'):self.cancel(folder)
        self.assertEqual(p.state(str(self.root))[2]['activeRound'],folder.name)

    def test_cancel_refuses_accepted_and_path_escape(self):
        self.bootstrap();rid=p.state(str(self.root))[2]['lastAcceptedRound']
        with self.assertRaisesRegex(ValueError,'accepted'):self.cancel(self.root/'.gpt-pm/rounds'/rid)
        with self.assertRaisesRegex(ValueError,'Invalid'):self.call(p.cancel_unsent,round='../escape',reason='x',manager_idle=True,evidence=str(self.report))

    def test_migration_blocks_active_and_requires_idle(self):
        self.prepare();self.legacy()
        with self.assertRaisesRegex(ValueError,'active'):self.migrate()
        with self.assertRaisesRegex(ValueError,'idle'):self.migrate(manager_idle=False)

    def test_legacy_cannot_start_new_work(self):
        self.bootstrap();self.legacy()
        with self.assertRaisesRegex(ValueError,'Migrate'):self.call(p.begin)
        with self.assertRaisesRegex(ValueError,'Migrate'):self.prepare('stage')

    def test_migration_archives_exact_state_and_resets_gate(self):
        self.bootstrap();pm,data=self.legacy()
        data.update(status='complete',ownerAccepted=True);p.save(pm/'PROJECT.json',data)
        before=(pm/'PROJECT.json').read_bytes();goal=(pm/'GOAL.md').read_bytes()
        result=self.migrate();archive=pm/result['migrationArchive']
        self.assertEqual((archive/'PROJECT.json').read_bytes(),before)
        self.assertEqual((pm/'GOAL.md').read_bytes(),goal)
        self.assertFalse(result['bootstrapApproved']);self.assertFalse(result['ownerAccepted'])
        self.assertEqual(result['chatUrl'],data['chatUrl'])
        self.assertEqual(result['status'],'initializing')
        self.assertEqual(self.migrate()['migrationArchive'],result['migrationArchive'])

    def test_config_mismatch_blocks_prepare_and_pending_blocks_config(self):
        args=dict(manager_idle=True,evidence=str(self.report),mode='Work',model='GPT-6',reasoning='default',observed_mode='Chat',observed_model='GPT-6',observed_reasoning='default')
        self.call(p.configure,**args)
        with self.assertRaisesRegex(ValueError,'configuration'):self.prepare()
        args['observed_mode']='Work';self.call(p.configure,**args);self.prepare()
        with self.assertRaisesRegex(ValueError,'idle boundary'):self.call(p.configure,**args)

if __name__=='__main__':unittest.main()
