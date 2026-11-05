import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Parser import Parser
from gdo.base.Render import Mode
from gdo.net.method.wget import GDT_WgetUrl, wget
from gdo.video.method.starwars import starwars


class StarWarsWgetTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    async def test_nested_local_file_flows_to_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'hello.txt'
            path.write_text('Hello Mr Moderator', encoding='utf-8')
            outer, inner = starwars(), wget()
            user = MagicMock()
            user.is_authenticated.return_value = True
            user.has_permission.return_value = True
            inner._env_user = user
            inner.execute = AsyncMock(side_effect=inner.gdo_execute)
            parser = Parser(Mode.render_cli, None, None, None, None)
            with patch.object(parser, 'get_method', side_effect=lambda name: outer if name == 'video.starwars' else inner):
                parsed = parser.parse_line(f'video.starwars $(wget {path.as_uri()})')
            module = MagicMock()
            outer.reply = MagicMock(return_value='started')
            with patch('gdo.video.method.starwars.module_video.instance', return_value=module):
                self.assertEqual('started', await parsed._nested_execute(parsed, True))
            module.connector.starwars.assert_called_once_with('Hello Mr Moderator')

    def test_file_url_validation(self):
        field = GDT_WgetUrl('url').not_null()
        self.assertTrue(field.validate('file:///tmp/example.txt'))
        self.assertEqual('/tmp/a b.txt', field.to_value('file:///tmp/a%20b.txt')['path'])
        self.assertFalse(field.validate('file://remote/etc/passwd'))

    def test_non_owner_cannot_read(self):
        method = wget()
        method._env_user = MagicMock()
        method._env_user.is_authenticated.return_value = True
        method._env_user.has_permission.return_value = False
        method.param_value = MagicMock(return_value={'scheme': 'file', 'path': '/not-read'})
        method.param_val = MagicMock(return_value='GET')
        method.err = MagicMock(return_value='denied')
        self.assertEqual('denied', method.gdo_execute())
        method.err.assert_called_once_with('err_wget_file_owner')

    def test_http_requests_keep_using_http_client(self):
        method = wget()
        method.param_value = MagicMock(side_effect=lambda key: (
            {'scheme': 'https', 'host': 'example.test', 'port': 443, 'path': '/text'}
            if key == 'url' else False))
        method.param_val = MagicMock(return_value='GET')
        with patch('gdo.net.method.wget.httplib2.Http') as http:
            http.return_value.request.return_value = ({'content-type': 'text/plain; charset=utf-8'}, b'Hello')
            result = method.gdo_execute()
        http.return_value.request.assert_called_once_with('https://example.test:443/text', method='GET')
        self.assertEqual('Hello', result.render_txt())

    def test_file_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'real.txt').write_text('private', encoding='utf-8')
            (root / 'link.txt').symlink_to(root / 'real.txt')
            method = wget()
            method._env_user = MagicMock()
            method._env_user.is_authenticated.return_value = True
            method._env_user.has_permission.return_value = True
            method.param_value = MagicMock(return_value={'scheme': 'file', 'path': str(root / 'link.txt')})
            method.param_val = MagicMock(return_value='GET')
            method.err = MagicMock(return_value='denied')
            self.assertEqual('denied', method.gdo_execute())
            method.err.assert_called_once_with('err_wget_file_read')

    def test_file_size_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'large.txt'
            path.write_bytes(b'a' * 16385)
            method = wget()
            method._env_user = MagicMock()
            method._env_user.is_authenticated.return_value = True
            method._env_user.has_permission.return_value = True
            method.param_value = MagicMock(return_value={'scheme': 'file', 'path': str(path)})
            method.param_val = MagicMock(return_value='GET')
            method.err = MagicMock(return_value='too big')
            self.assertEqual('too big', method.gdo_execute())
            method.err.assert_called_once_with('err_wget_file_size')
