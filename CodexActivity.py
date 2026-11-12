"""Infer turn activity from a bounded tail of the configured Codex session log."""
import json
import os


class CodexActivity:
    status = 'unknown'
    TAIL_BYTES = 256 * 1024

    @classmethod
    def poll(cls, path):
        if not path:
            cls.status = 'unknown'
            return cls.status
        try:
            with open(path, 'rb') as stream:
                size = os.fstat(stream.fileno()).st_size
                stream.seek(max(0, size - cls.TAIL_BYTES))
                if size > cls.TAIL_BYTES:
                    stream.readline()
                data = stream.read(cls.TAIL_BYTES)
            # A partial final record must not become a state transition.
            lines = data.split(b'\n')[:-1]
            for line in reversed(lines):
                try:
                    event = json.loads(line)
                    if event.get('type') != 'event_msg':
                        continue
                    kind = event.get('payload', {}).get('type')
                    if kind == 'task_started':
                        cls.status = 'active'
                        return cls.status
                    if kind in ('task_complete', 'turn_aborted'):
                        cls.status = 'idle'
                        return cls.status
                except (ValueError, AttributeError, TypeError):
                    continue
        except OSError:
            pass
        cls.status = 'unknown'
        return cls.status
