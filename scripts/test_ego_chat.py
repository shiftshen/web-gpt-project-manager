"""Ego submission keeps a durable receipt when browser delivery is uncertain."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import ego_chat


class EgoChatTests(unittest.TestCase):
    def test_uncertain_submission_is_not_reported_as_sent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / 'PROMPT.txt'
            receipt = root / 'browser-receipt.json'
            prompt.write_text('ROUND_ID: round-123\nPlease review.', encoding='utf-8')
            args = SimpleNamespace(space=1, page='p1', prompt=str(prompt), receipt=str(receipt), expected_url=None)
            state = {'url': 'https://chatgpt.com/', 'busy': False, 'draft': '', 'hasEditor': True}
            with patch.object(ego_chat, 'js', side_effect=[state, False]), patch.object(ego_chat, 'invoke', side_effect=RuntimeError('delivery unknown')), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    ego_chat.send(args)
            self.assertEqual(error.exception.code, 2)
            saved = json.loads(receipt.read_text())
            self.assertEqual(saved['status'], 'uncertain')
            self.assertEqual(saved['roundId'], 'round-123')

    def test_duplicate_round_does_not_create_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / 'PROMPT.txt'
            receipt = root / 'browser-receipt.json'
            prompt.write_text('ROUND_ID: round-123\nPlease review.', encoding='utf-8')
            args = SimpleNamespace(space=1, page='p1', prompt=str(prompt), receipt=str(receipt), expected_url=None)
            state = {'url': 'https://chatgpt.com/', 'busy': False, 'draft': '', 'hasEditor': True}
            with patch.object(ego_chat, 'js', side_effect=[state, True]):
                with self.assertRaises(ValueError):
                    ego_chat.send(args)
            self.assertFalse(receipt.exists())


if __name__ == '__main__':
    unittest.main()
