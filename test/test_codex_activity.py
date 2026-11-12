import json
import os
import tempfile
import unittest

from gdo.video.CodexActivity import CodexActivity


class TestCodexActivity(unittest.TestCase):
    def test_turn_events_and_partial_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'session.jsonl')
            with open(path, 'w', encoding='utf-8') as stream:
                stream.write(json.dumps({'type': 'event_msg', 'payload': {'type': 'task_started'}}) + '\n')
                stream.write('{"type": "event_msg"')
            self.assertEqual('active', CodexActivity.poll(path))
            with open(path, 'w', encoding='utf-8') as stream:
                stream.write(json.dumps({'type': 'event_msg', 'payload': {'type': 'task_complete'}}) + '\n')
            self.assertEqual('idle', CodexActivity.poll(path))
        self.assertEqual('unknown', CodexActivity.poll(path))

    def test_ignores_non_lifecycle_events(self):
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8') as stream:
            stream.write(json.dumps({'type': 'event_msg', 'payload': {'type': 'task_started'}}) + '\n')
            stream.write(json.dumps({'type': 'event_msg', 'payload': {'type': 'item_completed'}}) + '\n')
            stream.flush()
            self.assertEqual('active', CodexActivity.poll(stream.name))
