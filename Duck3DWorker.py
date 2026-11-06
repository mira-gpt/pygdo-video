"""Render the GLB duck into RGBA frames in a separate process.

Control is newline-delimited JSON on stdin; stdout contains fixed-size RGBA
frames. No desktop, microphone or network access is required.
"""
import json
import math
import sys
import threading
import time
from pathlib import Path


def main():
    import gltf
    from panda3d.core import AmbientLight, DirectionalLight, NodePath, OrthographicLens, Vec4, loadPrcFileData
    from direct.showbase.ShowBase import ShowBase
    from direct.actor.Actor import Actor

    size, fps = 256, 15
    loadPrcFileData('', f'window-type offscreen\nwin-size {size} {size}\nframebuffer-alpha 1\naudio-library-name null\nsync-video false\nnotify-level warning')
    base = ShowBase(windowType='offscreen')
    base.setBackgroundColor(0, 0, 0, 0)
    root = NodePath(gltf.load_model(str(Path(__file__).parent / 'assets/duck/mira-duck.glb')))
    # Only the beak is skinned. Wrapping the entire scene as an Actor would
    # discard its unskinned body, eyes and feet.
    beak = Actor(root.find('**/Duck rig'), copy=False)
    beak.reparentTo(root)
    root.reparentTo(base.render)
    lens = OrthographicLens()
    lens.setFilmSize(2.7, 2.7)
    base.cam.node().setLens(lens)
    base.camera.setPos(2.8, -6, 2.5)
    base.camera.lookAt(0, 0, 1)
    light = AmbientLight('ambient')
    light.setColor(Vec4(.75, .75, .75, 1))
    base.render.setLight(base.render.attachNewNode(light))
    light = DirectionalLight('key')
    light.setColor(Vec4(.8, .8, .8, 1))
    light_node = base.render.attachNewNode(light)
    light_node.setHpr(30, -45, 0)
    base.render.setLight(light_node)

    lock = threading.Lock()
    state = {'mode': 'idle', 'speaking': False, 'running': True}

    def receive():
        for line in sys.stdin:
            try:
                request = json.loads(line)
                with lock:
                    if request.get('mode') in ('idle', 'quacking'):
                        state['mode'] = request['mode']
                    if isinstance(request.get('speaking'), bool):
                        state['speaking'] = request['speaking']
                    if request.get('stop') is True:
                        state['running'] = False
                        return
            except (ValueError, TypeError):
                continue
        with lock:
            state['running'] = False

    threading.Thread(target=receive, daemon=True).start()
    start = time.monotonic()
    try:
        while True:
            with lock:
                mode, speaking, running = state['mode'], state['speaking'], state['running']
            if not running:
                break
            t = time.monotonic() - start
            root.setR(math.sin(t * (5 if mode == 'quacking' else 1.4)) * (8 if mode == 'quacking' else 2))
            root.setZ(abs(math.sin(t * 5)) * .08 if mode == 'quacking' else .012 * math.sin(t * 1.4))
            for index, name in enumerate(('Foot', 'Foot.001')):
                foot = root.find('**/' + name)
                if not foot.isEmpty():
                    foot.setZ(.16 + (max(0, math.sin(t * 5 + index * math.pi)) * .08 if mode == 'quacking' else 0))
            for eye in ('Eye white', 'Eye white.001', 'Pupil', 'Pupil.001'):
                node = root.find('**/' + eye)
                if not node.isEmpty():
                    node.setSz(.12 if (t + 2) % 4.2 < .12 else 1)
            beak.pose('Duck rigAction', int(t * 24) % 32 if speaking else 0)
            base.graphicsEngine.renderFrame()
            texture = base.win.getScreenshot()
            data = bytes(texture.getRamImageAs('RGBA'))
            if len(data) != size * size * 4:
                raise RuntimeError('Unexpected duck framebuffer size')
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
            time.sleep(1 / fps)
    except BrokenPipeError:
        pass
    finally:
        base.destroy()


if __name__ == '__main__':
    main()
