import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.Drawing import Drawing
from gdo.video.DrawingProtocol import validate_line
from gdo.video.StarWarsIPC import encode_text
from gdo.video.method.draw import draw
from gdo.video.method.ipc_draw import ipc_draw
from gdo.video.method.stroke import stroke


class DrawingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_drawing_renders_ordered_strokes_and_rejects_invalid_data(self):
        drawing = Drawing()
        drawing.add(10, 50, 90, 50, '#ff0000', 2)
        frame = Image.new('RGB', (200, 100), 'black')
        self.assertTrue(drawing.draw(frame))
        self.assertEqual(frame.getpixel((100, 50)), (255, 0, 0))
        for line in [(0, 0, 101, 1, '#ffffff', 1), (0, 0, 1, 1, 'red', 1),
                     (0, 0, float('nan'), 1, '#ffffff', 1)]:
            with self.subTest(line=line), self.assertRaises(ValueError):
                validate_line(*line)

    def test_line_and_prompt_are_queued(self):
        db = MagicMock()
        db.is_in_transaction.return_value = False
        command = stroke()
        command.param_value = MagicMock(side_effect={'x1': 1., 'y1': 2., 'x2': 3., 'y2': 4., 'width': .5}.get)
        command.param_val = MagicMock(return_value='#ffffff')
        command.reply = MagicMock(return_value='queued')
        with patch.object(Application, 'db', return_value=db), patch('gdo.video.method.stroke.IPC.send_to_dog') as send:
            self.assertEqual(command.gdo_execute(), 'queued')
        send.assert_called_once_with('video.ipc_stroke', ['1.0', '2.0', '3.0', '4.0', '#ffffff', '0.5'])
        request = draw()
        request.param_value = MagicMock(return_value='draw a duck')
        request.reply = MagicMock(return_value='queued')
        with patch.object(Application, 'db', return_value=db), patch('gdo.video.method.draw.IPC.send_to_dog') as send:
            self.assertEqual(request.gdo_execute(), 'queued')
        self.assertEqual(send.call_args.args[0], 'video.ipc_draw')

    async def test_dog_clears_and_relays_prompt_without_interrupting(self):
        handler = ipc_draw()
        handler.param_val = MagicMock(return_value=encode_text('a duck'))
        handler.empty = MagicMock()
        module = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
             patch.object(Application, 'CONFIG_PATH', '/tmp/test.toml'), \
             patch('gdo.video.method.ipc_draw.module_video.instance', return_value=module), \
             patch('gdo.mira.util.send_to_mira') as send:
            await handler.gdo_execute()
        module.connector.clear_drawing.assert_called_once()
        self.assertIn('a duck', send.call_args.args[0])
        self.assertIn('/tmp/test.toml', send.call_args.args[0])
        self.assertEqual(send.call_args.kwargs['interrupt'], False)

    async def test_off_clears_without_prompting_agent(self):
        handler = ipc_draw()
        handler.param_val = MagicMock(return_value=encode_text('off'))
        handler.empty = MagicMock()
        module = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.ipc_draw.module_video.instance', return_value=module), \
             patch('gdo.mira.util.send_to_mira') as send:
            await handler.gdo_execute()
        module.connector.clear_drawing.assert_called_once()
        send.assert_not_called()
