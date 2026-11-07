"""Render the GLB duck into RGBA frames in a separate process.

Control is newline-delimited JSON on stdin; stdout contains fixed-size RGBA
frames. No desktop, microphone or network access is required.
"""
import json
import math
import random
import sys
import threading
import time
from pathlib import Path

TRANSITION_SECONDS = .7


def transition_weight(elapsed, duration=TRANSITION_SECONDS):
    """Smoothly interpolate between poses, clamped at both ends."""
    amount = max(0.0, min(1.0, elapsed / duration))
    return amount * amount * (3.0 - 2.0 * amount)


def main():
    import gltf
    from panda3d.core import AmbientLight, CardMaker, DirectionalLight, LineSegs, NodePath, OrthographicLens, TransparencyAttrib, Vec4, loadPrcFileData
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
    tongue_joint = beak.controlJoint(None, 'modelRoot', 'Tongue')
    tongue_y = tongue_joint.getY() if not tongue_joint.isEmpty() else 0
    wing_actor = Actor(root.find('**/Wing rig'), copy=False)
    wing_actor.reparentTo(root)
    wing_base = wing_actor.controlJoint(None, 'modelRoot', 'WingBase')
    wing_tip = wing_actor.controlJoint(None, 'modelRoot', 'WingTip')
    if wing_base.isEmpty() or wing_tip.isEmpty():
        raise RuntimeError('Duck wing joints are missing')
    root.reparentTo(base.render)
    tears = []
    for side in (-1, 1):
        card = CardMaker('cry tear')
        card.setFrame(-.045, .045, -.11, 0)
        tear = root.attachNewNode(card.generate())
        tear.setPos(side * .22, -.81, 1.51)
        tear.setColor(.18, .65, 1, 1)
        tear.setLightOff()
        tear.hide()
        tears.append(tear)
    marks = LineSegs('ouch marks')
    marks.setThickness(3)
    marks.setColor(1, .86, .12, 1)
    for side in (-1, 1):
        for z, dz in ((1.15, -.08), (1.42, .02), (1.68, .1)):
            marks.moveTo(side * .73, -.35, z)
            marks.drawTo(side * 1.03, -.35, z + dz)
    pain_marks = root.attachNewNode(marks.create())
    pain_marks.setLightOff()
    pain_marks.setTransparency(TransparencyAttrib.MAlpha)
    pain_marks.hide()
    halo_lines = LineSegs('halo')
    halo_lines.setThickness(3)
    halo_lines.setColor(1, .9, .25, 1)
    for point in range(49):
        angle = point * math.tau / 48
        (halo_lines.moveTo if point == 0 else halo_lines.drawTo)(.28 * math.cos(angle), .13 * math.sin(angle), 0)
    halo = root.attachNewNode(halo_lines.create())
    halo.setPos(0, 0, 2.15)
    halo.setLightOff()
    halo.hide()
    brows = LineSegs('angry eyebrows')
    brows.setThickness(5)
    brows.setColor(.25, .08, .01, 1)
    for side in (-1, 1):
        brows.moveTo(side * .10, -.79, 1.70)
        brows.drawTo(side * .35, -.75, 1.82)
    angry_brows = root.attachNewNode(brows.create())
    angry_brows.setLightOff()
    angry_brows.hide()
    dizzy_spirals = []
    for index in range(5):
        spiral = LineSegs('dizzy spiral')
        spiral.setThickness(2)
        spiral.setColor(.8, .72, .3, 1)
        for point in range(32):
            angle = point * math.tau * 1.8 / 31
            radius = .005 + .045 * point / 31
            (spiral.moveTo if point == 0 else spiral.drawTo)(radius * math.cos(angle), 0, radius * math.sin(angle))
        node = root.attachNewNode(spiral.create())
        node.setBillboardPointEye()
        node.setLightOff()
        node.hide()
        dizzy_spirals.append(node)
    fuzz_lines = LineSegs('dizzy fuzz')
    fuzz_lines.setThickness(2)
    fuzz_lines.setColor(.8, .72, .3, 1)
    for point in range(30):
        x = -.19 + point * .38 / 29
        z = .025 * math.sin(point * .75)
        (fuzz_lines.moveTo if point == 0 else fuzz_lines.drawTo)(x, 0, z)
    fuzz = root.attachNewNode(fuzz_lines.create())
    fuzz.setBillboardPointEye()
    fuzz.setLightOff()
    fuzz.hide()
    mug = root.attachNewNode('beer mug')
    mug.setBillboardPointEye()
    mug.setLightOff()
    mug_outline = LineSegs('mug outline')
    mug_outline.setThickness(2)
    mug_outline.setColor(1, .85, .5, 1)
    for i, (x, z) in enumerate(((-.10, .20), (-.09, 0), (.09, 0), (.10, .20), (-.10, .20), (-.10, .16), (-.16, .16), (-.16, .05), (-.09, .05))):
        (mug_outline.moveTo if i == 0 else mug_outline.drawTo)(x, 0, z)
    mug.attachNewNode(mug_outline.create())
    beer_card = CardMaker('beer fill')
    beer_card.setFrame(-.08, .08, 0, 1)
    beer = mug.attachNewNode(beer_card.generate())
    beer.setColor(.85, .45, .06, 1)
    foam_lines = LineSegs('beer foam')
    foam_lines.setThickness(3)
    foam_lines.setColor(1, .98, .82, 1)
    for point in range(25):
        x = -.08 + point * .16 / 24
        (foam_lines.moveTo if point == 0 else foam_lines.drawTo)(x, -.003, .015 * abs(math.sin(point * .8)))
    foam = mug.attachNewNode(foam_lines.create())
    mug.hide()
    mugs = [(mug, beer, foam)]
    for index in range(3):
        copy = mug.copyTo(root)
        mugs.append((copy, copy.find('**/beer fill'), copy.find('**/beer foam')))
    barf_drops = []
    for index in range(4):
        card = CardMaker('barf drop')
        card.setFrame(-.04, .04, -.04, .04)
        drop = base.render.attachNewNode(card.generate())
        drop.setColor(.35, .8, .12, 1)
        drop.setBillboardPointEye()
        drop.setLightOff()
        drop.hide()
        barf_drops.append(drop)
    notes = []
    for index in range(6):
        lines = LineSegs('music note')
        lines.setThickness(3)
        lines.setColor(1, .85, .15, 1)
        for point in range(17):
            angle = point * math.tau / 16
            x, z = .055 * math.cos(angle), .035 * math.sin(angle)
            (lines.moveTo if point == 0 else lines.drawTo)(x, 0, z)
        lines.moveTo(.052, 0, 0)
        lines.drawTo(.052, 0, .20)
        lines.drawTo(.13, 0, .16)
        note = base.render.attachNewNode(lines.create())
        note.setBillboardPointEye()
        note.setLightOff()
        note.hide()
        notes.append(note)
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
    state = {'mode': 'idle', 'mode_start': time.monotonic(), 'speaking': False, 'running': True, 'envelope': [], 'step_ms': 50, 'speech_start': 0, 'gain': 0.0, 'frequency_hz': None}

    def receive():
        for line in sys.stdin:
            try:
                request = json.loads(line)
                with lock:
                    if request.get('mode') in ('idle', 'quacking', 'lol', 'shrug', 'sad', 'cry', 'ouch', 'hello', 'rolleye', 'high', 'music', 'tipsy', 'drunk', 'barf', 'embarrassed', 'plz', 'angry'):
                        state['mode'] = request['mode']
                        state['mode_start'] = time.monotonic()
                    if isinstance(request.get('speaking'), bool):
                        state['speaking'] = request['speaking']
                        state['envelope'] = []
                    gain = request.get('gain')
                    if isinstance(gain, (int, float)) and math.isfinite(gain):
                        state['gain'] = max(0.0, min(1.0, gain))
                        frequency = request.get('frequency_hz')
                        state['frequency_hz'] = frequency if isinstance(frequency, (int, float)) and math.isfinite(frequency) and frequency >= 0 else None
                    levels = request.get('envelope')
                    step = request.get('step_ms')
                    if isinstance(levels, list) and len(levels) <= 2400 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in levels) and isinstance(step, int) and 10 <= step <= 500:
                        state['envelope'], state['step_ms'], state['speech_start'] = levels, step, time.monotonic()
                    if request.get('stop') is True:
                        state['running'] = False
                        return
            except (ValueError, TypeError):
                continue
        with lock:
            state['running'] = False

    threading.Thread(target=receive, daemon=True).start()
    start = time.monotonic()
    nodes = [(root, 'R'), (root, 'Z'), (root, 'P'), (root, 'Sz')]
    nodes.extend([(wing_base, 'R'), (wing_tip, 'R')])
    for name, prop in [('Wing L', 'R'), ('Foot', 'Z'), ('Foot.001', 'Z'),
                       ('Eye white', 'Sz'), ('Eye white.001', 'Sz'), ('Pupil', 'Sz'), ('Pupil.001', 'Sz')]:
        node = root.find('**/' + name)
        if not node.isEmpty():
            nodes.append((node, prop))
    pupils = [root.find('**/' + name) for name in ('Pupil', 'Pupil.001')]
    bloodshot_veins = []
    for name in ('Eye white', 'Eye white.001'):
        eye = root.find('**/' + name)
        if eye.isEmpty():
            continue
        veins = LineSegs('bloodshot veins')
        veins.setThickness(1)
        veins.setColor(.65, .16, .16, 1)
        for side in (-1, 1):
            veins.moveTo(side * .16, -.075, .08)
            veins.drawTo(side * .115, -.105, .035)
            veins.drawTo(side * .08, -.12, .025)
            veins.moveTo(side * .115, -.105, .035)
            veins.drawTo(side * .13, -.09, -.005)
            veins.moveTo(side * .16, -.075, -.08)
            veins.drawTo(side * .10, -.11, -.04)
        vein_node = eye.attachNewNode(veins.create())
        vein_node.setLightOff()
        vein_node.hide()
        bloodshot_veins.append(vein_node)
    pupil_origins = [(node.getX(), node.getZ()) for node in pupils if not node.isEmpty()]
    pupils = [node for node in pupils if not node.isEmpty()]
    for node in pupils:
        nodes.extend([(node, 'X'), (node, 'Z'), (node, 'Sx')])
    previous_mode = 'idle'
    outgoing_mode = 'idle'
    transition_stamp = state['mode_start']
    origin = [getattr(node, 'get' + prop)() for node, prop in nodes]
    head = root.find('**/Head')
    next_hiccup = start + random.uniform(4, 10)
    hiccup_at = 0
    sway_rates = (1.7, 1.1, .37)
    next_tongue, tongue_until = start + random.uniform(3, 8), 0
    next_angry_flap, angry_flap_until = start + random.uniform(2, 5), 0
    next_scowl, scowl_start, scowl_duration = start + random.uniform(2, 5), 0, 1
    dizzy_kind, dizzy_until, dizzy_count, dizzy_offset, mug_count = 'none', 0, 0, 0.0, 0
    try:
        while True:
            with lock:
                mode, speaking, running = state['mode'], state['speaking'], state['running']
                mode_start = state['mode_start']
                envelope, step_ms, speech_start = state['envelope'], state['step_ms'], state['speech_start']
                gain, frequency = state['gain'], state['frequency_hz']
            if not running:
                break
            if mode_start != transition_stamp:
                origin = [getattr(node, 'get' + prop)() for node, prop in nodes]
                outgoing_mode, previous_mode = previous_mode, mode
                transition_stamp = mode_start
                sway_rates = (random.uniform(1.3, 1.9), random.uniform(.8, 1.3), random.uniform(.25, .5))
            blend = transition_weight(time.monotonic() - mode_start)
            t = time.monotonic() - start
            now = time.monotonic()
            if mode == 'angry' and now >= next_scowl:
                scowl_start = now
                scowl_duration = random.uniform(.8, 1.6)
                next_scowl = now + scowl_duration + random.uniform(2, 5)
            elif mode != 'angry':
                scowl_start = 0
                next_scowl = now + random.uniform(2, 5)
            scowl = math.sin(math.pi * (now - scowl_start) / scowl_duration) if scowl_start and now - scowl_start < scowl_duration else 0
            if mode == 'angry' and now >= next_angry_flap:
                angry_flap_until = now + random.uniform(.6, 1.2)
                next_angry_flap = angry_flap_until + random.uniform(3, 7)
            elif mode != 'angry':
                angry_flap_until = 0
                next_angry_flap = now + random.uniform(2, 5)
            angry_flapping = mode == 'angry' and now < angry_flap_until
            if mode == 'drunk' and now >= next_tongue:
                tongue_until = now + random.uniform(.7, 1.4)
                next_tongue = tongue_until + random.uniform(5, 12)
            elif mode != 'drunk':
                tongue_until = 0
                next_tongue = now + random.uniform(3, 8)
            if mode == 'tipsy' and now >= next_hiccup:
                hiccup_at = now
                next_hiccup = now + random.uniform(5, 12)
            elif mode != 'tipsy':
                hiccup_at = 0
                next_hiccup = now + random.uniform(4, 10)
            if not head.isEmpty():
                if mode == 'embarrassed':
                    head.setColorScale(1, .17, .17, 1)
                else:
                    head.clearColorScale()
            root.setR(math.sin(t * (7 if mode == 'lol' else 5 if mode == 'quacking' else 1.4)) * (12 if mode == 'lol' else 8 if mode == 'quacking' else 2))
            root.setZ(abs(math.sin(t * 8)) * .22 if mode == 'lol' else abs(math.sin(t * 5)) * .08 if mode == 'quacking' else .012 * math.sin(t * 1.4))
            root.setP(20 + 2 * math.sin(t * .8) if mode in ('sad', 'cry') else 0)
            if mode == 'angry':
                angry_brows.show()
                angry_brows.setSx(1 - .18 * scowl)
                angry_brows.setZ(-.06 * scowl)
                root.setP(-7 + 1.5 * math.sin(t * 1.8))
                if angry_flapping:
                    root.setZ(.12 * abs(math.sin(t * 9)))
            else:
                angry_brows.hide()
            if mode == 'plz':
                halo.show()
                root.setZ(.12 * abs(math.sin(t * 7)))
            else:
                halo.hide()
            if mode == 'music':
                root.setP(8 * math.sin(t * 3.2))
            for index, note in enumerate(notes):
                if mode == 'music' and index < min(len(notes), round(gain * 30)):
                    phase = (t * .35 + index / len(notes)) % 1
                    note.setPos(.65 + .12 * math.sin(t + index), -.4, 1.25 + phase * 1.0)
                    note.setColorScale(1, .5 + min(frequency or 0, 2000) / 4000, .5, 1)
                    note.show()
                else:
                    note.hide()
            if mode == 'high':
                root.setR(7 * math.sin(t * 1.1))
            for vein in bloodshot_veins:
                vein.show() if mode == 'drunk' else vein.hide()
            if mode == 'drunk' and now >= dizzy_until:
                dizzy_kind = random.choice(('spiral', 'spiral', 'fuzz', 'mug', 'both'))
                dizzy_until = now + random.uniform(2.5, 5.0)
                dizzy_count = random.randint(3, 5)
                mug_count = random.randint(2, 4)
                dizzy_offset = random.uniform(-.6, .6)
                for _, fill, froth in mugs:
                    level = random.uniform(.06, .18)
                    fill.setSz(level)
                    froth.setZ(level)
                    froth.setScale(1, 1, random.uniform(.5, 1.5))
            for index, spiral in enumerate(dizzy_spirals):
                if mode == 'drunk' and dizzy_kind in ('spiral', 'both') and index < dizzy_count:
                    phase = t * 1.1 + dizzy_offset + index * math.tau / dizzy_count
                    spiral.setPos(.42 * math.sin(phase), -.1 + .18 * math.cos(phase), 2.04 + .08 * math.cos(phase))
                    spiral.show()
                else:
                    spiral.hide()
            if mode == 'drunk' and dizzy_kind == 'fuzz':
                fuzz.setPos(.1 * math.sin(t), -.1, 2.05 + .025 * math.sin(t * 2))
                fuzz.show()
            else:
                fuzz.hide()
            for index, (mug_node, _, _) in enumerate(mugs):
                if mode == 'drunk' and dizzy_kind in ('mug', 'both') and index < mug_count:
                    phase = t * 1.1 + dizzy_offset + index * math.tau / mug_count
                    mug_node.setPos(.50 * math.sin(phase), -.1 + .20 * math.cos(phase), 1.89 + .09 * math.cos(phase))
                    mug_node.show()
                else:
                    mug_node.hide()
            if mode in ('tipsy', 'drunk'):
                root.setR((8 if mode == 'tipsy' else 20) * (.8 * math.sin(t * sway_rates[0]) + .2 * math.sin(t * sway_rates[2])))
                root.setP((3 if mode == 'tipsy' else 10) * math.sin(t * sway_rates[1]))
                if mode == 'tipsy' and hiccup_at and now - hiccup_at < .35:
                    root.setZ(root.getZ() + .12 * math.sin(math.pi * (now - hiccup_at) / .35))
            if mode == 'barf':
                root.setP(28 + 8 * math.sin(t * 9))
            for index, drop in enumerate(barf_drops):
                if mode == 'barf':
                    phase = (t * 1.5 + index / len(barf_drops)) % 1
                    drop.setPos(.1 + phase * .55, -.9, 1.3 - phase * .85)
                    drop.show()
                else:
                    drop.hide()
            root.setSz(.88 + .012 * math.sin(t * (7 if mode == 'cry' else .8)) if mode in ('sad', 'cry') else 1)
            for tear in tears:
                if mode == 'cry':
                    tear.show()
                    tear.setZ(1.51 - .15 * ((time.monotonic() - mode_start) % .8) / .8)
                else:
                    tear.hide()
            if mode == 'shrug':
                elapsed = time.monotonic() - mode_start
                root.setR(4 * math.sin(elapsed * 18) * max(0, 1 - elapsed))
                root.setZ(.40 * math.sin(math.pi * min(elapsed / .65, 1)))
            if mode == 'ouch':
                phase = (time.monotonic() - mode_start) * 7
                root.setR(16 * math.sin(phase))
                root.setZ(.16 * abs(math.sin(phase)))
            if mode == 'hello':
                phase = (time.monotonic() - mode_start) * 18
                root.setR(5 * math.sin(phase / 2))
                root.setZ(.05 * abs(math.sin(phase / 2)))
            if mode == 'ouch' or (outgoing_mode == 'ouch' and blend < 1):
                pain_marks.show()
                pain_marks.setColorScale(1, 1, 1, blend if mode == 'ouch' else 1 - blend)
            else:
                pain_marks.hide()
            left_wing = root.find('**/Wing L')
            if not left_wing.isEmpty():
                left_wing.setR(-(30 + 25 * math.sin(t * 11)) if mode in ('lol', 'plz') or angry_flapping else -55 if mode == 'shrug' else 25 if mode in ('sad', 'cry') else 0)
            if mode == 'hello':
                wave = math.sin((time.monotonic() - mode_start) * 18)
                wing_base.setR(50 + 30 * wave)
                wing_tip.setR(30 * wave)
            else:
                wing_base.setR(30 + 25 * math.sin(t * 11) if mode in ('lol', 'plz') or angry_flapping else 55 if mode == 'shrug' else -25 if mode in ('sad', 'cry') else 0)
                wing_tip.setR(0)
            for index, name in enumerate(('Foot', 'Foot.001')):
                foot = root.find('**/' + name)
                if not foot.isEmpty():
                    if mode == 'ouch':
                        lift = max(0, math.sin((time.monotonic() - mode_start) * 7 + index * math.pi)) * .22
                    else:
                        lift = max(0, math.sin(t * 5 + index * math.pi)) * .08 if mode in ('quacking', 'lol') else 0
                    foot.setZ(.16 + lift)
            for eye in ('Eye white', 'Eye white.001', 'Pupil', 'Pupil.001'):
                node = root.find('**/' + eye)
                if not node.isEmpty():
                    node.setSz(1.35 if mode in ('shrug', 'plz') else .12 if (t + 2) % 4.2 < .12 else .25 if mode == 'cry' else .42 if mode in ('sad', 'high') else .7 - .28 * scowl if mode == 'angry' else 1)
                    if eye.startswith('Eye white'):
                        if mode in ('high', 'drunk'):
                            node.setColorScale(1, .35 if mode == 'high' else .55, .35 if mode == 'high' else .55, 1)
                        else:
                            node.clearColorScale()
            for pupil, (x, z) in zip(pupils, pupil_origins):
                phase = (time.monotonic() - mode_start) * 5
                pupil.setX(x + .035 * math.sin(phase) if mode == 'rolleye' else x)
                pupil.setZ(z + .045 * math.cos(phase) if mode == 'rolleye' else z)
                pupil.setSx(1 - .7 * scowl if mode == 'angry' else 1)
            if blend < 1:
                for (node, prop), start_value in zip(nodes, origin):
                    target_value = getattr(node, 'get' + prop)()
                    getattr(node, 'set' + prop)(start_value + (target_value - start_value) * blend)
            index = int((time.monotonic() - speech_start) * 1000 / step_ms)
            level = envelope[index] if speaking and 0 <= index < len(envelope) else 0
            # The existing animation opens its beak around frame 7.
            tongue_out = mode == 'drunk' and now < tongue_until and not speaking
            beak.pose('Duck rigAction', 7 if tongue_out else int(t * 24) % 32 if speaking and not envelope else round(level * 7))
            if not tongue_joint.isEmpty():
                tongue_joint.setY(tongue_y - .24 if tongue_out else tongue_y)
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
