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


def music_note_count(gain, capacity=6):
    """Keep a few notes visible even when audio features are unavailable."""
    return min(capacity, 2 + round(max(0.0, min(1.0, gain)) * 80))


def music_bounce(previous, gain):
    """Smooth a sensitive microphone level into a gentle dance pulse."""
    target = min(1.0, max(0.0, gain) * 20)
    return previous + (target - previous) * (.45 if target > previous else .18)


def metal_head_pitch(pulse):
    """Nod harder on audio-level peaks; this is not a tempo detector."""
    return 3 + 30 * max(0.0, min(1.0, pulse))


def sleep_mouth_frame(elapsed):
    """Two quiet beak smacks occasionally; speech still takes precedence."""
    phase = elapsed % 11.0
    return 4 if 7.0 <= phase < 7.13 or 7.3 <= phase < 7.43 else 0


def goth_hair_motion(elapsed):
    """Snap the fringe aside, then let it fall back slowly."""
    phase = elapsed % 9.0
    if phase < 4.0:
        return 0.0, 0.0
    if phase < 4.22:
        amount = (phase - 4.0) / .22
    elif phase < 5.0:
        amount = 1.0
    elif phase < 8.0:
        amount = 1.0 - (phase - 5.0) / 3.0
    else:
        amount = 0.0
    head = max(0.0, 1.0 - abs(phase - 4.18) / .35)
    return amount, head


def spell_bat_position(elapsed, index, count):
    """Spread rising bats within the duck overlay's visible area."""
    phase = (elapsed * .22 + index / count) % 1
    x = max(-.95, min(.95, -.72 + index * .35 + .09 * math.sin(elapsed * 1.3 + index)))
    return x, 1.15 + 1.0 * phase


def transition_weight(elapsed, duration=TRANSITION_SECONDS):
    """Smoothly interpolate between poses, clamped at both ends."""
    amount = max(0.0, min(1.0, elapsed / duration))
    return amount * amount * (3.0 - 2.0 * amount)


def main():
    import gltf
    from panda3d.core import AmbientLight, CardMaker, DirectionalLight, Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat, GeomVertexWriter, LineSegs, NodePath, OrthographicLens, TextNode, TransparencyAttrib, Vec4, loadPrcFileData
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
    # Keep the eyes and beak together when the head snaps back.
    head_pivot = root.attachNewNode('head pivot')
    head_pivot.setPos(0, -.32, 1.05)
    for name in ('Head', 'Eye white', 'Eye white.001', 'Pupil', 'Pupil.001'):
        part = root.find('**/' + name)
        if not part.isEmpty():
            part.wrtReparentTo(head_pivot)
    beak.wrtReparentTo(head_pivot)
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
    sorry_lines = LineSegs('sorry eyebrows')
    sorry_lines.setThickness(3)
    sorry_lines.setColor(.3, .16, .05, 1)
    for side in (-1, 1):
        sorry_lines.moveTo(side * .1, -.79, 1.81)
        sorry_lines.drawTo(side * .34, -.75, 1.72)
    sorry_brows = root.attachNewNode(sorry_lines.create())
    sorry_brows.setLightOff()
    sorry_brows.hide()
    teacher = root.attachNewNode('teacher accessories')
    accessories = LineSegs('glasses beard and pointer')
    accessories.setThickness(3)
    accessories.setColor(.12, .08, .04, 1)
    for side in (-1, 1):
        for point in range(33):
            angle = math.tau * point / 32
            (accessories.moveTo if point == 0 else accessories.drawTo)(side * .22 + .17 * math.cos(angle), -.84, 1.59 + .15 * math.sin(angle))
    accessories.moveTo(-.05, -.85, 1.59)
    accessories.drawTo(.05, -.85, 1.59)
    for side in (-1, 1):
        accessories.moveTo(side * .19, -.82, 1.25)
        accessories.drawTo(side * .13, -.86, .98)
        accessories.drawTo(0, -.88, .87)
    accessories.moveTo(.52, -.55, 1.0)
    accessories.drawTo(1.03, -.5, 1.75)
    teacher.attachNewNode(accessories.create()).setLightOff()
    board = teacher.attachNewNode('chalkboard')
    board.setPos(-.7, .45, 1.95)
    board.setBillboardPointEye()
    board_card = CardMaker('chalkboard surface')
    board_card.setFrame(-.42, .42, -.21, .21)
    board_surface = board.attachNewNode(board_card.generate())
    board_surface.setColor(.04, .18, .11, 1)
    board_surface.setLightOff()
    chalk = TextNode('chalk title')
    chalk.setText('ToDo:')
    chalk.setTextColor(.95, .95, .85, 1)
    chalk_node = board.attachNewNode(chalk)
    chalk_node.setPos(-.33, -.01, .02)
    chalk_node.setScale(.13)
    chalk_node.setLightOff()
    teacher.hide()
    sleep_letters = []
    sleep_font_path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    sleep_font = base.loader.loadFont(str(sleep_font_path)) if sleep_font_path.is_file() else None
    if sleep_font and hasattr(sleep_font, 'setOutline'):
        sleep_font.setOutline((.05, .05, .07, 1), 1.2, .2)
    for index in range(3):
        letter = TextNode(f'sleep Z {index}')
        letter.setText('Z')
        letter.setTextColor(.9, .95, 1, 1)
        if sleep_font:
            letter.setFont(sleep_font)
        else:
            letter.setShadow(.06, .06)
            letter.setShadowColor(.05, .05, .07, 1)
        node = root.attachNewNode(letter)
        node.setBillboardPointEye()
        node.setScale(.13 + index * .025)
        node.setLightOff()
        node.hide()
        sleep_letters.append(node)
    nerd = root.attachNewNode('nerd glasses and teeth')
    glasses = LineSegs('large glasses')
    glasses.setThickness(5)
    glasses.setColor(.06, .045, .03, 1)
    for side in (-1, 1):
        for point in range(33):
            angle = math.tau * point / 32
            (glasses.moveTo if point == 0 else glasses.drawTo)(side * .22 + .21 * math.cos(angle), -.88, 1.59 + .19 * math.sin(angle))
    glasses.moveTo(-.04, -.88, 1.59)
    glasses.drawTo(.04, -.88, 1.59)
    nerd.attachNewNode(glasses.create()).setLightOff()
    for side in (-1, 1):
        tooth = CardMaker('front tooth')
        tooth.setFrame(-.043, .043, -.14, 0)
        tooth_node = nerd.attachNewNode(tooth.generate())
        tooth_node.setPos(side * .045, -.99, 1.29)
        tooth_node.setColor(1, .98, .88, 1)
        tooth_node.setLightOff()
    nerd.hide()
    rich = root.attachNewNode('rich costume')
    for name, frame, color in (
        ('top hat', (-.22, .22, 1.91, 2.28), (.07, .05, .09, 1)),
        ('hat brim', (-.33, .33, 1.88, 1.94), (.07, .05, .09, 1)),
        ('gold hat band', (-.22, .22, 1.95, 2.01), (.95, .7, .08, 1)),
    ):
        card = CardMaker(name)
        card.setFrame(*frame)
        piece = rich.attachNewNode(card.generate())
        piece.setY(-.35)
        piece.setColor(*color)
        piece.setLightOff()
    monocle = LineSegs('gold monocle')
    monocle.setThickness(4)
    monocle.setColor(1, .78, .12, 1)
    for point in range(33):
        angle = math.tau * point / 32
        (monocle.moveTo if point == 0 else monocle.drawTo)(.22 + .15 * math.cos(angle), -.91, 1.59 + .15 * math.sin(angle))
    monocle.moveTo(.32, -.91, 1.48)
    monocle.drawTo(.48, -.91, .96)
    rich.attachNewNode(monocle.create()).setLightOff()
    dollar = TextNode('rich dollar sign')
    dollar.setText('$')
    dollar.setTextColor(1, .78, .12, 1)
    dollar_node = rich.attachNewNode(dollar)
    dollar_node.setPos(-.09, -.84, .55)
    dollar_node.setScale(.3)
    dollar_node.setLightOff()
    rich.hide()
    anon = root.attachNewNode('anonymous mask')
    for name, frame, color in (
        ('anon red top hat', (-.22, .22, 1.91, 2.28), (.72, .04, .07, 1)),
        ('anon red hat brim', (-.33, .33, 1.88, 1.94), (.55, .02, .04, 1)),
        ('anon hat band', (-.22, .22, 1.95, 2.01), (.12, .03, .04, 1)),
    ):
        card = CardMaker(name)
        card.setFrame(*frame)
        piece = anon.attachNewNode(card.generate())
        piece.setY(-.35)
        piece.setColor(*color)
        piece.setLightOff()
    # A rounded forehead, cheekbones and tapered chin, rather than a rectangle.
    contour = [(-.29, 1.76), (-.35, 1.68), (-.36, 1.53), (-.33, 1.38),
               (-.25, 1.27), (-.12, 1.19), (0, 1.16), (.12, 1.19),
               (.25, 1.27), (.33, 1.38), (.36, 1.53), (.35, 1.68),
               (.29, 1.76), (.17, 1.81), (0, 1.83), (-.17, 1.81)]
    mask_vertices = GeomVertexData('mask face', GeomVertexFormat.getV3(), Geom.UHStatic)
    writer = GeomVertexWriter(mask_vertices, 'vertex')
    writer.addData3(0, 0, 1.5)
    for x, z in contour:
        writer.addData3(x, 0, z)
    triangles = GeomTriangles(Geom.UHStatic)
    for index in range(len(contour)):
        triangles.addVertices(0, index + 1, (index + 1) % len(contour) + 1)
    geometry = Geom(mask_vertices)
    geometry.addPrimitive(triangles)
    mask_node = GeomNode('mask face')
    mask_node.addGeom(geometry)
    mask_face = anon.attachNewNode(mask_node)
    mask_face.setY(-1.05)
    mask_face.setColor(.95, .94, .85, 1)
    mask_face.setLightOff()
    mask_face.setTwoSided(True)
    features = LineSegs('mask grin and moustache')
    features.setThickness(4)
    features.setColor(.1, .07, .06, 1)
    for side in (-1, 1):
        features.moveTo(side * .06, -1.07, 1.63)
        features.drawTo(side * .29, -1.07, 1.70)
        features.moveTo(side * .07, -1.07, 1.54)
        features.drawTo(side * .25, -1.07, 1.56)
        features.moveTo(0, -1.07, 1.37)
        features.drawTo(side * .17, -1.07, 1.34)
        features.drawTo(side * .28, -1.07, 1.42)
        features.moveTo(side * .23, -1.07, 1.29)
        features.drawTo(0, -1.07, 1.24)
    features.moveTo(0, -1.07, 1.24)
    features.drawTo(0, -1.07, 1.19)
    anon.attachNewNode(features.create()).setLightOff()
    anon.hide()
    king = root.attachNewNode('king crown and brows')
    crown_shape = [(-.32, 1.88), (.32, 1.88), (.34, 2.17), (.19, 2.05),
                   (0, 2.25), (-.19, 2.05), (-.34, 2.17)]
    crown_data = GeomVertexData('crown', GeomVertexFormat.getV3(), Geom.UHStatic)
    crown_writer = GeomVertexWriter(crown_data, 'vertex')
    crown_writer.addData3(0, 0, 1.96)
    for x, z in crown_shape:
        crown_writer.addData3(x, 0, z)
    crown_triangles = GeomTriangles(Geom.UHStatic)
    for index in range(len(crown_shape)):
        crown_triangles.addVertices(0, index + 1, (index + 1) % len(crown_shape) + 1)
    crown_geom = Geom(crown_data)
    crown_geom.addPrimitive(crown_triangles)
    crown_node = GeomNode('crown')
    crown_node.addGeom(crown_geom)
    crown = king.attachNewNode(crown_node)
    crown.setY(-.35)
    crown.setColor(1, .72, .05, 1)
    crown.setLightOff()
    crown.setTwoSided(True)
    royal_brows = LineSegs('regal brows')
    royal_brows.setColor(.20, .12, .03, 1)
    royal_brows.setThickness(4)
    for side in (-1, 1):
        royal_brows.moveTo(side * .07, -.91, 1.74)
        royal_brows.drawTo(side * .35, -.91, 1.70)
    king.attachNewNode(royal_brows.create()).setLightOff()
    sceptre = LineSegs('royal sceptre')
    sceptre.setColor(1, .72, .08, 1)
    sceptre.setThickness(6)
    sceptre.moveTo(.66, -.82, .48)
    sceptre.drawTo(.85, -.82, 1.48)
    for point in range(25):
        angle = math.tau * point / 24
        (sceptre.moveTo if point == 0 else sceptre.drawTo)(
            .85 + .10 * math.cos(angle), -.82, 1.55 + .10 * math.sin(angle))
    king.attachNewNode(sceptre.create()).setLightOff()
    king.hide()
    rambo = root.attachNewNode('cartoon action costume')
    for name, frame, y, color in (
        ('cigar', (.10, .42, 1.23, 1.28), -1.08, (.34, .15, .05, 1)),
        ('cigar ember', (.40, .44, 1.23, 1.28), -1.09, (1, .25, .03, 1)),
        ('machine gun body', (.30, .85, .85, 1.04), -.86, (.13, .14, .15, 1)),
        ('machine gun barrel', (.83, 1.25, .92, .98), -.86, (.16, .17, .18, 1)),
        ('machine gun grip', (.42, .51, .70, .87), -.86, (.15, .12, .09, 1)),
    ):
        card = CardMaker(name)
        card.setFrame(*frame)
        part = rambo.attachNewNode(card.generate())
        part.setY(y)
        part.setColor(*color)
        part.setLightOff()
    belt = LineSegs('ammo belt')
    belt.setThickness(6)
    belt.setColor(.8, .58, .15, 1)
    for index in range(10):
        x = -.3 + index * .065
        z = 1.0 - index * .035
        belt.moveTo(x, -.90, z)
        belt.drawTo(x + .035, -.90, z - .065)
    rambo.attachNewNode(belt.create()).setLightOff()
    flash_lines = LineSegs('cartoon muzzle flash')
    flash_lines.setThickness(4)
    flash_lines.setColor(1, .72, .1, 1)
    for angle in range(0, 360, 45):
        a = math.radians(angle)
        flash_lines.moveTo(1.25, -.88, .95)
        flash_lines.drawTo(1.25 + .16 * math.cos(a), -.88, .95 + .16 * math.sin(a))
    muzzle_flash = rambo.attachNewNode(flash_lines.create())
    muzzle_flash.setLightOff()
    rambo.hide()
    hippi = root.attachNewNode('hippi peace and joint')
    scarf_card = CardMaker('hippi scarf')
    scarf_card.setFrame(-.34, .34, .97, 1.06)
    scarf = hippi.attachNewNode(scarf_card.generate())
    scarf.setY(-.83)
    scarf.setColor(.78, .23, .53, 1)
    scarf.setLightOff()
    scarf_tail_card = CardMaker('hippi scarf tail')
    scarf_tail_card.setFrame(-.13, .03, .72, .99)
    scarf_tail = hippi.attachNewNode(scarf_tail_card.generate())
    scarf_tail.setY(-.84)
    scarf_tail.setColor(.78, .23, .53, 1)
    scarf_tail.setLightOff()
    sign = hippi.attachNewNode('peace sign')
    peace = LineSegs('peace symbol')
    peace.setThickness(4)
    peace.setColor(.95, .84, .28, 1)
    for point in range(33):
        angle = point * math.tau / 32
        (peace.moveTo if point == 0 else peace.drawTo)(.14 * math.cos(angle), 0, .14 * math.sin(angle))
    peace.moveTo(0, 0, .14)
    peace.drawTo(0, 0, -.14)
    for side in (-1, 1):
        peace.moveTo(0, 0, 0)
        peace.drawTo(side * .10, 0, -.10)
    sign.attachNewNode(peace.create()).setLightOff()
    sign.setPos(-.83, -.85, 1.35)
    joint_card = CardMaker('joint')
    joint_card.setFrame(.10, .40, 1.23, 1.27)
    joint = hippi.attachNewNode(joint_card.generate())
    joint.setY(-1.08)
    joint.setColor(.92, .89, .75, 1)
    joint.setLightOff()
    smoke_puffs = []
    for index in range(3):
        smoke = LineSegs('joint smoke')
        smoke.setThickness(2)
        smoke.setColor(.72, .76, .79, .8)
        for point in range(20):
            z = point * .012
            x = .025 * math.sin(point * .55 + index)
            (smoke.moveTo if point == 0 else smoke.drawTo)(x, 0, z)
        puff = hippi.attachNewNode(smoke.create())
        puff.setLightOff()
        smoke_puffs.append(puff)
    hippi.hide()
    goth = root.attachNewNode('goth outfit and cigarette')
    goth_face = head_pivot.attachNewNode('goth face and cigarette')
    goth_face.setPos(0, .32, -1.05)
    for name, frame, y, color in (
        ('cigarette', (.18, .48, 1.33, 1.37), -1.12, (.92, .90, .81, 1)),
        ('cigarette ember', (.47, .50, 1.33, 1.37), -1.13, (1, .20, .03, 1)),
    ):
        card = CardMaker(name)
        card.setFrame(*frame)
        part = goth_face.attachNewNode(card.generate())
        part.setY(y)
        part.setColor(*color)
        part.setLightOff()
    goth_lines = LineSegs('goth eye circles')
    goth_lines.setThickness(2)
    goth_lines.setColor(.34, .22, .32, 1)
    for side in (-1, 1):
        goth_lines.moveTo(side * .12, -.86, 1.49)
        goth_lines.drawTo(side * .21, -.86, 1.47)
        goth_lines.drawTo(side * .30, -.86, 1.49)
    goth_face.attachNewNode(goth_lines.create()).setLightOff()
    cross = LineSegs('silver christian cross')
    cross.setThickness(5)
    cross.setColor(.82, .84, .88, 1)
    cross.moveTo(0, -1.0, .93)
    cross.drawTo(0, -1.0, .53)
    cross.moveTo(-.13, -1.0, .81)
    cross.drawTo(.13, -1.0, .81)
    goth.attachNewNode(cross.create()).setLightOff()
    # A dark crown and asymmetrical fringe, attached to the existing head
    # pivot so the hair moves with the head rather than floating beside it.
    goth_hair = head_pivot.attachNewNode('goth black hair')
    goth_hair.setPos(0, .32, -1.05)
    goth_hair.setLightOff()
    crown_data = GeomVertexData('goth hair crown', GeomVertexFormat.getV3(), Geom.UHStatic)
    crown_writer = GeomVertexWriter(crown_data, 'vertex')
    crown_points = [(-.43, 1.72), (-.42, 1.91), (-.30, 2.02), (-.15, 2.09),
                    (0, 2.11), (.15, 2.09), (.30, 2.02), (.42, 1.91),
                    (.43, 1.72), (.23, 1.82), (0, 1.86), (-.23, 1.82)]
    for x, z in crown_points:
        crown_writer.addData3(x, -.65, z)
    crown_triangles = GeomTriangles(Geom.UHStatic)
    for index in range(1, len(crown_points) - 1):
        crown_triangles.addVertices(0, index, index + 1)
    crown_geom = Geom(crown_data)
    crown_geom.addPrimitive(crown_triangles)
    crown_node = GeomNode('black hair crown')
    crown_node.addGeom(crown_geom)
    crown = goth_hair.attachNewNode(crown_node)
    crown.setColor(.025, .018, .035, 1)
    crown.setTwoSided(True)
    fringe = goth_hair.attachNewNode('goth fringe')
    fringe.setPos(.04, -1.08, 1.94)
    fringe_lines = LineSegs('black locks over one eye')
    fringe_lines.setThickness(12)
    fringe_lines.setColor(.025, .015, .035, 1)
    for shift in (-.045, 0, .045):
        fringe_lines.moveTo(shift, 0, 0)
        fringe_lines.drawTo(.09 + shift, 0, -.15)
        fringe_lines.drawTo(.17 + shift, 0, -.30)
        fringe_lines.drawTo(.13 + shift, 0, -.42)
    fringe.attachNewNode(fringe_lines.create())
    goth_hair.hide()
    goth_smoke = [puff.copyTo(goth_face) for puff in smoke_puffs]
    goth_face.hide()
    goth.hide()
    metal = root.attachNewNode('metal horns')
    horns = LineSegs('raised metal hand')
    horns.setThickness(7)
    horns.setColor(1, .75, .10, 1)
    # Palm and the extended index and little finger form the horns gesture.
    horns.moveTo(-.76, -.87, 1.05)
    horns.drawTo(-.76, -.87, 1.30)
    horns.drawTo(-.86, -.87, 1.54)
    horns.drawTo(-.85, -.87, 1.28)
    horns.drawTo(-.97, -.87, 1.27)
    horns.drawTo(-1.02, -.87, 1.53)
    horns.drawTo(-1.08, -.87, 1.26)
    horns.drawTo(-1.03, -.87, 1.08)
    horns.drawTo(-.76, -.87, 1.05)
    metal.attachNewNode(horns.create()).setLightOff()
    metal.hide()
    ninja = root.attachNewNode('ninja accessories')
    for name, frame, y, color in (
        ('ninja mask', (-.37, .37, 1.18, 1.42), -1.06, (.035, .035, .045, 1)),
        ('ninja headband', (-.32, .32, 1.77, 1.83), -.85, (.12, .12, .14, 1)),
        ('ninja sash', (-.43, .43, .61, .68), -.70, (.14, .14, .16, 1)),
    ):
        card = CardMaker(name)
        card.setFrame(*frame)
        part = ninja.attachNewNode(card.generate())
        part.setY(y)
        part.setColor(*color)
        part.setLightOff()
    tools = LineSegs('ninja sword and star')
    tools.setThickness(4)
    tools.setColor(.65, .69, .74, 1)
    tools.moveTo(.52, -.35, .55)
    tools.drawTo(.96, -.35, 1.65)
    tools.moveTo(.50, -.35, .72)
    tools.drawTo(.66, -.35, .67)
    for point in range(9):
        angle = point * math.pi / 4
        radius = .13 if point % 2 == 0 else .05
        (tools.moveTo if point == 0 else tools.drawTo)(-.85 + radius * math.cos(angle), -.83, 1.30 + radius * math.sin(angle))
    ninja.attachNewNode(tools.create()).setLightOff()
    ninja.hide()
    news = root.attachNewNode('news presenter')
    paper_card = CardMaker('news paper')
    paper_card.setFrame(-.29, .29, .56, .96)
    paper = news.attachNewNode(paper_card.generate())
    paper.setY(-1.0)
    paper.setColor(.96, .96, .90, 1)
    paper.setLightOff()
    paper_lines = LineSegs('news paper lines')
    paper_lines.setThickness(2)
    paper_lines.setColor(.2, .23, .28, 1)
    for z in (.89, .84, .79, .74, .69, .64):
        paper_lines.moveTo(-.23, -1.02, z)
        paper_lines.drawTo(.20, -1.02, z)
    news.attachNewNode(paper_lines.create()).setLightOff()
    news_brows = LineSegs('focused news brows')
    news_brows.setThickness(3)
    news_brows.setColor(.24, .15, .04, 1)
    for side in (-1, 1):
        news_brows.moveTo(side * .08, -.9, 1.73)
        news_brows.drawTo(side * .32, -.9, 1.75)
    news.attachNewNode(news_brows.create()).setLightOff()
    news.hide()
    pirate = root.attachNewNode('pirate costume')
    for name, frame, y, color in (
        ('pirate eyepatch', (-.34, -.09, 1.52, 1.72), -.97, (.035, .035, .04, 1)),
        ('pirate shirt', (-.39, .39, .49, .98), -.84, (.10, .10, .12, 1)),
        ('pirate flag', (-.23, .23, .64, .87), -.86, (.035, .035, .04, 1)),
        ('pirate hook black plastic flap', (-.80, -.62, .88, 1.06), -.94, (.035, .04, .05, 1)),
        ('parrot body', (.44, .67, 1.26, 1.58), -.82, (.09, .69, .28, 1)),
        ('parrot head', (.47, .65, 1.54, 1.72), -.84, (.12, .78, .35, 1)),
        ('parrot beak', (.61, .74, 1.58, 1.66), -.86, (1, .65, .06, 1)),
        ('parrot eye', (.57, .61, 1.64, 1.68), -.87, (.03, .03, .03, 1)),
    ):
        card = CardMaker(name)
        card.setFrame(*frame)
        part = pirate.attachNewNode(card.generate())
        part.setY(y)
        part.setColor(*color)
        part.setLightOff()
    pirate_lines = LineSegs('pirate patch strap hook and skull')
    pirate_lines.setThickness(5)
    pirate_lines.setColor(.08, .08, .09, 1)
    pirate_lines.moveTo(-.31, -.95, 1.69)
    pirate_lines.drawTo(.28, -.95, 1.87)
    pirate_lines.setColor(.75, .77, .80, 1)
    pirate_lines.moveTo(-.65, -.91, .98)
    pirate_lines.drawTo(-.82, -.91, .87)
    for point in range(18):
        angle = math.pi * (1 + point / 17)
        pirate_lines.drawTo(-.82 + .13 * math.cos(angle), -.91, .99 + .13 * math.sin(angle))
    pirate_lines.setColor(.96, .96, .90, 1)
    for x in (-.09, .09):
        pirate_lines.moveTo(x, -.88, .69)
        pirate_lines.drawTo(-x, -.88, .82)
    for point in range(25):
        angle = math.tau * point / 24
        (pirate_lines.moveTo if point == 0 else pirate_lines.drawTo)(.065 * math.cos(angle), -.88, .78 + .065 * math.sin(angle))
    pirate.attachNewNode(pirate_lines.create()).setLightOff()
    pirate.hide()
    work = root.attachNewNode('construction worker costume')
    for name, frame, y, color in (
        ('hard hat crown', (-.34, .34, 1.82, 2.02), -.35, (1, .72, .04, 1)),
        ('hard hat brim', (-.43, .43, 1.80, 1.85), -.37, (1, .60, .02, 1)),
        ('blue overalls', (-.38, .38, .42, .86), -.86, (.08, .25, .65, 1)),
        ('left strap', (-.32, -.20, .82, 1.12), -.88, (.08, .25, .65, 1)),
        ('right strap', (.20, .32, .82, 1.12), -.88, (.08, .25, .65, 1)),
    ):
        card = CardMaker(name)
        card.setFrame(*frame)
        part = work.attachNewNode(card.generate())
        part.setY(y)
        part.setColor(*color)
        part.setLightOff()
    drill = work.attachNewNode('pneumatic drill')
    for name, frame, color in (
        ('drill handle', (.40, .78, 1.04, 1.10), (.12, .12, .13, 1)),
        ('drill housing', (.49, .69, .51, 1.08), (.38, .40, .42, 1)),
        ('drill bit', (.56, .62, .17, .53), (.65, .67, .69, 1)),
    ):
        card = CardMaker(name)
        card.setFrame(*frame)
        part = drill.attachNewNode(card.generate())
        part.setY(-1.0)
        part.setColor(*color)
        part.setLightOff()
    work.hide()
    birthday = root.attachNewNode('birthday party')
    hat_data = GeomVertexData('birthday hat', GeomVertexFormat.getV3(), Geom.UHStatic)
    hat_vertices = GeomVertexWriter(hat_data, 'vertex')
    for x, z in ((-.30, 1.85), (.30, 1.85), (.02, 2.23)):
        hat_vertices.addData3(x, 0, z)
    hat_faces = GeomTriangles(Geom.UHStatic)
    hat_faces.addVertices(0, 1, 2)
    hat_mesh = Geom(hat_data)
    hat_mesh.addPrimitive(hat_faces)
    hat_node = GeomNode('birthday hat')
    hat_node.addGeom(hat_mesh)
    party_hat = birthday.attachNewNode(hat_node)
    party_hat.setY(-.35)
    party_hat.setColor(.80, .12, .50, 1)
    party_hat.setLightOff()
    party_hat.setTwoSided(True)
    for name, frame, y, color in (
        ('cake plate', (-.57, .57, .06, .12), -1.13, (.85, .91, 1, 1)),
        ('birthday cake', (-.49, .49, .12, .42), -1.14, (.63, .29, .12, 1)),
        ('cake icing', (-.50, .50, .39, .46), -1.16, (1, .74, .80, 1)),
        ('blower mouthpiece', (.19, .36, 1.22, 1.27), -1.06, (1, .76, .15, 1)),
    ):
        card = CardMaker(name)
        card.setFrame(*frame)
        part = birthday.attachNewNode(card.generate())
        part.setY(y)
        part.setColor(*color)
        part.setLightOff()
        part.setTwoSided(True)
    blower = birthday.attachNewNode('party blower unrolling')
    blower.setPos(.35, -1.08, 1.245)
    blower_card = CardMaker('party blower paper')
    blower_card.setFrame(0, .54, -.045, .045)
    blower_paper = blower.attachNewNode(blower_card.generate())
    blower_paper.setColor(.20, .72, .96, 1)
    blower_paper.setLightOff()
    blower_paper.setTwoSided(True)
    flames = []
    for index in range(46):
        row, column = divmod(index, 23)
        x = -.44 + column * .04
        z = .46 + row * .08
        y = -1.18 + row * .10
        candle_card = CardMaker('birthday candle')
        candle_card.setFrame(-.009, .009, 0, .095)
        candle = birthday.attachNewNode(candle_card.generate())
        candle.setPos(x, y, z)
        candle.setColor(*((1, .92, .34, 1) if index % 2 else (.32, .72, 1, 1)))
        candle.setLightOff()
        candle.setTwoSided(True)
        flame_card = CardMaker('birthday candle flame')
        flame_card.setFrame(-.010, .010, 0, .045)
        flame = birthday.attachNewNode(flame_card.generate())
        flame.setPos(x, y - .01, z + .095)
        flame.setColor(1, .55, .06, 1)
        flame.setLightOff()
        flame.setTwoSided(True)
        flames.append(flame)
    birthday.hide()
    magic = root.attachNewNode('wizard costume and frog')
    wizard_hat = GeomVertexData('wizard hat', GeomVertexFormat.getV3(), Geom.UHStatic)
    hat_writer = GeomVertexWriter(wizard_hat, 'vertex')
    for x, z in ((-.28, 1.86), (.28, 1.86), (.04, 2.23)):
        hat_writer.addData3(x, 0, z)
    hat_triangle = GeomTriangles(Geom.UHStatic)
    hat_triangle.addVertices(0, 1, 2)
    hat_geom = Geom(wizard_hat)
    hat_geom.addPrimitive(hat_triangle)
    hat_node = GeomNode('wizard hat')
    hat_node.addGeom(hat_geom)
    hat = magic.attachNewNode(hat_node)
    hat.setY(-.35)
    hat.setColor(.26, .13, .52, 1)
    hat.setLightOff()
    hat.setTwoSided(True)
    hat_brim = CardMaker('wizard hat brim')
    hat_brim.setFrame(-.34, .34, 1.84, 1.91)
    brim = magic.attachNewNode(hat_brim.generate())
    brim.setY(-.36)
    brim.setColor(.18, .08, .35, 1)
    brim.setLightOff()
    robe = CardMaker('wizard robe')
    robe.setFrame(-.55, .55, -.38, .38)
    robe_node = magic.attachNewNode(robe.generate())
    robe_node.setPos(0, -.57, .69)
    robe_node.setColor(.22, .12, .55, 1)
    robe_node.setLightOff()
    wand_lines = LineSegs('magic wand')
    wand_lines.setThickness(4)
    wand_lines.setColor(.45, .24, .09, 1)
    wand_lines.moveTo(.47, -.85, .93)
    wand_lines.drawTo(.94, -.85, 1.65)
    magic.attachNewNode(wand_lines.create()).setLightOff()
    frog_card = CardMaker('frog')
    frog_card.setFrame(-.15, .15, -.08, .08)
    frog = magic.attachNewNode(frog_card.generate())
    frog.setPos(-.78, -.45, .12)
    frog.setColor(.2, .75, .2, 1)
    frog.setLightOff()
    for side in (-1, 1):
        eye_card = CardMaker('frog eye')
        eye_card.setFrame(-.035, .035, -.035, .035)
        frog_eye = magic.attachNewNode(eye_card.generate())
        frog_eye.setPos(-.78 + side * .085, -.46, .20)
        frog_eye.setColor(.45, .95, .25, 1)
        frog_eye.setLightOff()
    stars = []
    bats = []
    for index in range(5):
        bat_lines = LineSegs('spell bat')
        bat_lines.setThickness(4)
        bat_lines.setColor(.08, .05, .12, 1)
        for x, z in ((-.16, .03), (-.10, .10), (-.04, .03), (0, .07), (.04, .03), (.10, .10), (.16, .03)):
            (bat_lines.moveTo if x == -.16 else bat_lines.drawTo)(x, 0, z)
        bat = magic.attachNewNode(bat_lines.create())
        bat.setBillboardPointEye()
        bat.setLightOff()
        bats.append(bat)
    for index in range(5):
        star_lines = LineSegs('spell sparkle')
        star_lines.setThickness(3)
        star_lines.setColor(.9, .75, 1, 1)
        star_lines.moveTo(-.06, 0, 0)
        star_lines.drawTo(.06, 0, 0)
        star_lines.moveTo(0, 0, -.06)
        star_lines.drawTo(0, 0, .06)
        star = magic.attachNewNode(star_lines.create())
        star.setBillboardPointEye()
        star.setLightOff()
        stars.append(star)
    magic.hide()
    zombie_marks = root.attachNewNode('zombie patches')
    patches = LineSegs('zombie marks')
    patches.setThickness(6)
    patches.setColor(.18, .35, .08, 1)
    for x, y, z, mark_size in ((-.30, -.60, .8, .13), (.27, -.60, .65, .10), (-.25, -.75, 1.39, .08), (.35, -.5, .94, .08)):
        patches.moveTo(x - mark_size / 2, y, z)
        patches.drawTo(x + mark_size / 2, y, z + mark_size / 3)
    zombie_marks.attachNewNode(patches.create()).setLightOff()
    zombie_marks.hide()
    zombie_skin = [root.find('**/' + name) for name in ('Body', 'Head', 'Wing L')]
    zombie_skin.append(wing_actor)
    skin_colors = [(skin, skin.hasColor(), skin.getColor()) for skin in zombie_skin if not skin.isEmpty()]
    # GLB textures/materials live on GeomNodes and override parent colors.
    # Save their original render states so leaving goth restores the model.
    goth_skin_geometry = [(geometry, geometry.getState())
                          for skin, _, _ in skin_colors if skin.getName() == 'Body'
                          for geometry in skin.findAllMatches('**/+GeomNode')]
    sand_card = CardMaker('giveup sand')
    sand_card.setFrame(-.65, .65, -.4, .4)
    sand = base.render.attachNewNode(sand_card.generate())
    sand.setP(-90)
    sand.setPos(0, -.42, -.12)
    sand.setColor(.78, .64, .36, 1)
    sand.setLightOff()
    sand.hide()
    tail_lines = LineSegs('giveup limp tail')
    tail_lines.setThickness(5)
    tail_lines.setColor(1, .8, .08, 1)
    tail_lines.moveTo(0, .42, .86)
    tail_lines.drawTo(0, .70, .73)
    tail_lines.drawTo(0, .76, .50)
    tail = root.attachNewNode(tail_lines.create())
    tail.setLightOff()
    tail.hide()
    smile_lines = LineSegs('happy smile')
    smile_lines.setThickness(3)
    smile_lines.setColor(.35, .09, .02, 1)
    for point in range(21):
        x = -.18 + .36 * point / 20
        (smile_lines.moveTo if point == 0 else smile_lines.drawTo)(x, -.94, 1.30 + 1.5 * x * x)
    smile = root.attachNewNode(smile_lines.create())
    smile.setLightOff()
    smile.hide()
    happy_lines = LineSegs('happy closed eyes')
    happy_lines.setThickness(4)
    happy_lines.setColor(.08, .04, .02, 1)
    for side in (-1, 1):
        happy_lines.moveTo(side * .34, -.83, 1.57)
        happy_lines.drawTo(side * .22, -.85, 1.66)
        happy_lines.drawTo(side * .10, -.83, 1.57)
    happy_eyes = root.attachNewNode(happy_lines.create())
    happy_eyes.setLightOff()
    happy_eyes.hide()
    hearts = []
    for index in range(5):
        lines = LineSegs('heart')
        lines.setThickness(3)
        lines.setColor(1, .22, .4, 1)
        for point in range(49):
            angle = math.tau * point / 48
            x = .0045 * 16 * math.sin(angle) ** 3
            z = .0045 * (13 * math.cos(angle) - 5 * math.cos(2 * angle) - 2 * math.cos(3 * angle) - math.cos(4 * angle))
            (lines.moveTo if point == 0 else lines.drawTo)(x, 0, z)
        heart = root.attachNewNode(lines.create())
        heart.setBillboardPointEye()
        heart.setLightOff()
        heart.hide()
        hearts.append(heart)
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
    # Flat, camera-facing drink props in the same style as the other costumes.
    drinks = []
    for name, outline, frame, color in (
        ('whiskey', [(-.11, .27), (-.09, 0), (.09, 0), (.11, .27), (-.11, .27)], (-.075, .075, .03, .14), (.72, .35, .06, 1)),
        ('beer bottle', [(-.085, 0), (-.085, .22), (-.035, .30), (-.035, .42), (.035, .42), (.035, .30), (.085, .22), (.085, 0), (-.085, 0)], (-.065, .065, .025, .17), (.62, .31, .04, 1)),
        ('wine glass', [(-.12, .32), (-.10, .18), (-.04, .12), (0, .11), (0, 0), (-.07, 0), (.07, 0), (0, 0), (0, .11), (.04, .12), (.10, .18), (.12, .32), (-.12, .32)], (-.07, .07, .14, .21), (.65, .06, .14, 1)),
    ):
        drink = root.attachNewNode('cheers ' + name)
        drink.setBillboardPointEye()
        drink.setLightOff()
        lines = LineSegs(name + ' outline')
        lines.setThickness(3)
        lines.setColor(.95, .91, .78, 1)
        for index, (x, z) in enumerate(outline):
            (lines.moveTo if index == 0 else lines.drawTo)(x, -.01, z)
        drink.attachNewNode(lines.create())
        card = CardMaker(name + ' liquid')
        card.setFrame(*frame)
        liquid = drink.attachNewNode(card.generate())
        liquid.setColor(*color)
        drink.hide()
        drinks.append((drink, liquid))
    barf_drops = []
    for index in range(20):
        chunk = index % 3 == 0
        card = CardMaker('barf drop')
        width = (.055 + .012 * (index % 3)) if chunk else (.025 + .008 * (index % 3))
        card.setFrame(-width, width, -width * .7, width * .7)
        drop = base.render.attachNewNode(card.generate())
        drop.setColor(*((.38, .23, .07, 1) if chunk else (.32, .75, .10, 1)))
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
                    if request.get('mode') in ('idle', 'quacking', 'lol', 'shrug', 'sad', 'cry', 'ouch', 'hello', 'rolleye', 'high', 'music', 'tipsy', 'drunk', 'barf', 'embarrassed', 'plz', 'teacher', 'xd', 'sorry', 'nerd', 'cast', 'zombie', 'giveup', 'rich', 'anon', 'king', 'turnaround', 'shiver', 'rambo', 'hippi', 'metal', 'ninja', 'news', 'pirate', 'ghost', 'work', 'bday', 'hah', 'cheers', 'goth', 'angry', 'inlove', 'trip', 'tired', 'zzz'):
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
    nodes = [(root, 'R'), (root, 'Z'), (root, 'P'), (root, 'Sz'), (head_pivot, 'P')]
    head_node = root.find('**/Head')
    if not head_node.isEmpty():
        nodes.append((head_node, 'H'))
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
    next_happy_eyes, happy_eyes_until = start + random.uniform(2, 5), 0
    next_trip_look, trip_look_start, trip_look_duration, trip_direction = start + random.uniform(4, 9), 0, 3, 1
    next_trip_hiccup, trip_hiccup_at = start + random.uniform(12, 25), 0
    next_yawn, yawn_until = start + random.uniform(6, 12), 0
    next_goth_glance, goth_glance_start, goth_glance_duration = start + random.uniform(4, 8), 0, 2.5
    heart_speeds = [random.uniform(.20, .35) for _ in hearts]
    dizzy_kind, dizzy_until, dizzy_count, dizzy_offset, mug_count = 'none', 0, 0, 0.0, 0
    music_pulse = 0.0
    skin_override = None
    cheers_drink = 0
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
                if mode == 'cheers':
                    cheers_drink = random.randrange(len(drinks))
                sway_rates = (random.uniform(1.3, 1.9), random.uniform(.8, 1.3), random.uniform(.25, .5))
            blend = transition_weight(time.monotonic() - mode_start)
            t = time.monotonic() - start
            now = time.monotonic()
            if mode == 'goth':
                if now >= next_goth_glance:
                    goth_glance_start = now
                    goth_glance_duration = random.uniform(2, 3.5)
                    next_goth_glance = now + goth_glance_duration + random.uniform(5, 11)
            else:
                goth_glance_start = 0
                next_goth_glance = now + random.uniform(4, 8)
            goth_glance = (math.sin(math.pi * (now - goth_glance_start) / goth_glance_duration)
                           if goth_glance_start and now - goth_glance_start < goth_glance_duration else 0)
            if mode == 'tired' and now >= next_yawn:
                yawn_until = now + random.uniform(1.1, 2.0)
                next_yawn = yawn_until + random.uniform(8, 16)
            elif mode != 'tired':
                yawn_until = 0
                next_yawn = now + random.uniform(6, 12)
            if mode == 'trip':
                if now >= next_trip_look:
                    trip_look_start = now
                    trip_look_duration = random.uniform(3, 5)
                    trip_direction = random.choice((-1, 1))
                    next_trip_look = now + trip_look_duration + random.uniform(5, 12)
                if now >= next_trip_hiccup:
                    trip_hiccup_at = now
                    next_trip_hiccup = now + random.uniform(15, 30)
            else:
                trip_look_start = trip_hiccup_at = 0
                next_trip_look = now + random.uniform(4, 9)
                next_trip_hiccup = now + random.uniform(12, 25)
            trip_look = math.sin(math.pi * (now - trip_look_start) / trip_look_duration) * trip_direction if trip_look_start and now - trip_look_start < trip_look_duration else 0
            if mode == 'inlove' and now >= next_happy_eyes:
                happy_eyes_until = now + random.uniform(.6, 1.3)
                next_happy_eyes = happy_eyes_until + random.uniform(2, 6)
            elif mode != 'inlove':
                happy_eyes_until = 0
                next_happy_eyes = now + random.uniform(2, 5)
            happy_closed = mode in ('xd', 'zzz') or (mode == 'inlove' and now < happy_eyes_until)
            for index, letter in enumerate(sleep_letters):
                if mode == 'zzz':
                    phase = ((now - mode_start) * .18 + index / 3) % 1
                    letter.setPos(.37 + .12 * phase, -.85, 1.88 + .35 * phase)
                    letter.show()
                else:
                    letter.hide()
            smile.show() if mode in ('inlove', 'xd', 'trip') else smile.hide()
            happy_eyes.show() if happy_closed else happy_eyes.hide()
            for index, heart in enumerate(hearts):
                if mode == 'inlove':
                    phase = (t * heart_speeds[index] + index / len(hearts)) % 1
                    heart.setPos((-.55 if index % 2 else .55) + .07 * math.sin(t * 2 + index), -.2, 1.3 + phase * .95)
                    heart.setScale(.7 + .3 * math.sin(math.pi * phase))
                    heart.show()
                else:
                    heart.hide()
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
                elif mode != 'zombie':
                    head.clearColorScale()
            new_skin_override = mode if mode in ('shiver', 'ninja', 'goth') else None
            if new_skin_override != skin_override:
                skin_override = new_skin_override
                for geometry, original_state in goth_skin_geometry:
                    if skin_override == 'goth':
                        geometry.setTextureOff(100)
                        geometry.setMaterialOff(100)
                        geometry.setColor(.07, .07, .09, 1, 100)
                    else:
                        geometry.setState(original_state)
                for skin, had_color, original_color in skin_colors:
                    if skin_override == 'shiver':
                        skin.setColor(.58, .68, .76, 1, 1)
                    elif skin_override == 'ninja':
                        skin.setColor(.07, .07, .09, 1, 1)
                    elif skin_override == 'goth' and skin.getName() == 'Body':
                        skin.setColor(.07, .07, .09, 1, 100)
                    elif had_color:
                        skin.setColor(original_color)
                    else:
                        skin.clearColor()
            for skin in zombie_skin:
                if skin.isEmpty():
                    continue
                if mode == 'zombie':
                    skin.setColorScale(.45, .95, .32, 1)
                elif mode == 'goth' and skin.getName() == 'Body':
                    # The GLB supplies its own yellow material on child
                    # geometry. A high-priority scale darkens that material
                    # even when a plain NodePath color is overridden.
                    skin.setColorScale(.08, .08, .09, 1, 100)
                elif skin != head or mode != 'embarrassed':
                    skin.clearColorScale()
            zombie_marks.show() if mode == 'zombie' else zombie_marks.hide()
            sand.show() if mode == 'giveup' else sand.hide()
            tail.show() if mode == 'giveup' else tail.hide()
            root.setR(math.sin(t * (7 if mode == 'lol' else 5 if mode == 'quacking' else 1.4)) * (12 if mode == 'lol' else 8 if mode == 'quacking' else 2))
            root.setH(360 * transition_weight(t, 3.0) if mode == 'turnaround' else 0)
            root.setZ(abs(math.sin(t * 8)) * .22 if mode == 'lol' else abs(math.sin(t * 5)) * .08 if mode == 'quacking' else .012 * math.sin(t * 1.4))
            if mode == 'ghost':
                root.setTransparency(TransparencyAttrib.MAlpha)
                root.setColorScale(.85, .95, 1, .38)
                root.setZ(.14 + .045 * math.sin(t * 1.5))
            else:
                root.clearTransparency()
                root.clearColorScale()
            root.setP(20 + 2 * math.sin(t * .8) if mode in ('sad', 'cry') else 0)
            if mode == 'shiver':
                root.setR(3.5 * math.sin(t * 19) + 1.5 * math.sin(t * 29))
                root.setP(5 + 2 * math.sin(t * 23))
                root.setZ(.015 * math.sin(t * 25))
            if not head.isEmpty():
                head.setH(28 * trip_look if mode == 'trip' else 0)
            if mode == 'trip':
                root.setR(0)
                root.setZ(.05 * math.sin(math.pi * min((now - trip_hiccup_at) / .3, 1)) if trip_hiccup_at and now - trip_hiccup_at < .3 else 0)
            elif mode == 'tired':
                root.setR(2 * math.sin(t * .45))
                root.setP(10 + 4 * math.sin(t * .4))
            elif mode == 'zzz':
                root.setR(2 * math.sin(t * .45))
                root.setP(8 + 1.5 * math.sin(t * .5))
            if mode == 'sorry':
                sorry_brows.show()
                root.setP(10 + 1.5 * math.sin(t * 1.2))
                root.setR(4 * math.sin(t * .7))
            else:
                sorry_brows.hide()
            teacher.show() if mode == 'teacher' else teacher.hide()
            nerd.show() if mode == 'nerd' else nerd.hide()
            rich.show() if mode == 'rich' else rich.hide()
            anon.show() if mode == 'anon' else anon.hide()
            king.show() if mode == 'king' else king.hide()
            rambo.show() if mode == 'rambo' else rambo.hide()
            hippi.show() if mode == 'hippi' else hippi.hide()
            goth.show() if mode == 'goth' else goth.hide()
            goth_face.show() if mode == 'goth' else goth_face.hide()
            goth_hair.show() if mode == 'goth' else goth_hair.hide()
            metal.show() if mode == 'metal' else metal.hide()
            ninja.show() if mode == 'ninja' else ninja.hide()
            news.show() if mode == 'news' else news.hide()
            pirate.show() if mode == 'pirate' else pirate.hide()
            work.show() if mode == 'work' else work.hide()
            birthday.show() if mode == 'bday' else birthday.hide()
            for index, (drink, liquid) in enumerate(drinks):
                if mode == 'cheers' and index == cheers_drink:
                    elapsed = now - mode_start
                    lift = min(1.0, elapsed / .55)
                    drink.setPos(.62, -.95, .75 + .58 * lift)
                    drink.setR(8 * math.sin(elapsed * 3))
                    liquid.setR(5 * math.sin(elapsed * 5) * math.exp(-elapsed * .35))
                    drink.show()
                else:
                    drink.hide()
            if mode == 'bday':
                phase = t % 5.0
                extension = max(0.0, min(1.0, (phase - .5) * 2, (2.5 - phase) * 2))
                blower.setSx(.18 + .82 * extension)
                for index, flame in enumerate(flames):
                    flame.setSz(.75 + .25 * math.sin(t * 9 + index * 1.7))
                    flame.setR(8 * math.sin(t * 7 + index * 1.3))
            if mode == 'work':
                drilling = (t % 5.0) < 1.5
                drill.setZ(.035 * math.sin(t * 35) if drilling else 0)
                root.setP(5 + 1.5 * math.sin(t * 24) if drilling else 0)
            if mode == 'pirate':
                root.setR(4 * math.sin(t * 1.5))
            if mode == 'news':
                root.setP(4 + 3 * math.sin(t * 3))
                root.setR(2 * math.sin(t * 2))
            if mode == 'ninja':
                root.setP(8 + 2 * math.sin(t * 1.5))
            music_pulse = music_bounce(music_pulse, gain) if mode in ('music', 'metal') else 0.0
            if mode == 'metal':
                root.setP(metal_head_pitch(music_pulse))
                root.setR(2 * music_pulse * math.sin(t * 6))
            if mode == 'hippi':
                sign.setR(18 * math.sin(t * 3))
                for index, puff in enumerate(smoke_puffs):
                    phase = (t * .35 + index / len(smoke_puffs)) % 1
                    puff.setPos(.40 + .04 * math.sin(t * 2 + index), -1.09, 1.27 + phase * .35)
                    puff.setScale(.6 + phase * .7)
            if mode == 'goth':
                root.setR(1.5 * math.sin(t * .8))
                fringe_lift, head_toss = goth_hair_motion(now - mode_start)
                fringe.setR(75 * fringe_lift)
                for index, puff in enumerate(goth_smoke):
                    phase = (t * .25 + index / len(goth_smoke)) % 1
                    puff.setPos(.50 + .025 * math.sin(t + index), -1.13, 1.37 + phase * .32)
                    puff.setScale(.5 + phase * .6)
            if mode == 'rambo':
                muzzle_flash.show() if int(t * 12) % 3 else muzzle_flash.hide()
                rambo.setR(1.5 * math.sin(t * 15))
            if mode == 'king':
                root.setP(-7 + math.sin(t * .5))
                root.setR(1.5 * math.sin(t * .6))
            if mode == 'anon':
                root.setR(8 * math.sin(t * 2.4) + 3 * math.sin(t * 4.8))
                root.setP(4 + 4 * math.sin(t * 2.4))
                root.setZ(.07 * max(0, math.sin(t * 2.4)))
            if mode == 'rich':
                root.setP(-8 + 2 * math.sin(t * .7))
                root.setR(3 * math.sin(t * .8))
            if mode == 'cast':
                magic.show()
                for index, bat in enumerate(bats):
                    x, z = spell_bat_position(t, index, len(bats))
                    bat.setPos(x, -.8, z)
                    bat.setSz(.55 + .45 * abs(math.sin(t * 8 + index)))
                for index, star in enumerate(stars):
                    phase = (t * .6 + index / len(stars)) % 1
                    star.setPos(.9 + .3 * phase, -.8, 1.6 + .45 * phase)
                    star.setScale(.5 + .5 * abs(math.sin(t * 5 + index)))
            else:
                magic.hide()
            if mode == 'angry':
                angry_brows.show()
                angry_brows.setSx(1 - .18 * scowl)
                angry_brows.setZ(-.06 * scowl)
                root.setP(-7 + 1.5 * math.sin(t * 1.8))
                if angry_flapping:
                    root.setZ(.12 * abs(math.sin(t * 9)))
            else:
                angry_brows.hide()
            if mode == 'zombie':
                root.setR(10 * math.sin(t * 1.3))
                root.setP(12 + 5 * math.sin(t * .8))
            if mode == 'giveup':
                root.setR(0)
                root.setP(75 + 1.5 * math.sin(t * 1.5))
                root.setZ(-.14)
            if mode == 'plz':
                halo.show()
                root.setZ(.12 * abs(math.sin(t * 7)))
            else:
                halo.hide()
            if mode == 'music':
                root.setP(3 * math.sin(t * 3.2) + 7 * music_pulse)
                root.setZ(.055 * music_pulse)
            for index, note in enumerate(notes):
                if mode == 'music' and index < music_note_count(gain, len(notes)):
                    phase = (t * .35 + index / len(notes)) % 1
                    note.setPos(.65 + .12 * math.sin(t + index), -.4, 1.25 + phase * 1.0)
                    note.setColorScale(1, .5 + min(frequency or 0, 2000) / 4000, .5, 1)
                    note.show()
                else:
                    note.hide()
            if mode in ('high', 'hippi'):
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
                    spread = ((index * 7) % 11 - 5) / 5
                    drop.setPos(.1 + phase * (.65 + .15 * spread), -.9,
                                1.3 + phase * .12 * spread - phase * phase * .95)
                    drop.setR((index * 37 + t * 90) % 360)
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
            if mode == 'hah':
                elapsed = time.monotonic() - mode_start
                pulse = min(1, elapsed / .12) * max(0, 1 - max(0, elapsed - .35) / .5)
                head_pivot.setP(-38 * pulse)
            elif mode == 'goth':
                head_pivot.setP(-25 * head_toss + 7 * goth_glance)
            else:
                head_pivot.setP(0)
            if mode == 'ouch' or (outgoing_mode == 'ouch' and blend < 1):
                pain_marks.show()
                pain_marks.setColorScale(1, 1, 1, blend if mode == 'ouch' else 1 - blend)
            else:
                pain_marks.hide()
            left_wing = root.find('**/Wing L')
            if not left_wing.isEmpty():
                left_wing.setR(-(30 + 25 * math.sin(t * 11)) if mode in ('lol', 'plz') or angry_flapping else -50 + 8 * math.sin(t * 7) if mode == 'metal' else -35 + 15 * math.sin(t * 3) if mode == 'hippi' else -55 if mode == 'shrug' else -70 if mode == 'zombie' else 25 if mode in ('sad', 'cry') else 0)
            if mode == 'hello':
                wave = math.sin((time.monotonic() - mode_start) * 18)
                wing_base.setR(50 + 30 * wave)
                wing_tip.setR(30 * wave)
            else:
                wing_base.setR(30 + 25 * math.sin(t * 11) if mode in ('lol', 'plz') or angry_flapping else 55 if mode in ('shrug', 'cheers') else 70 if mode == 'zombie' else -25 if mode in ('sad', 'cry') else 0)
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
                    node.setSz(.3 + .08 * math.sin(t * .6) if mode == 'tired' else 1.65 if mode == 'trip' and eye.startswith('Pupil') else 1 if mode == 'trip' else .05 if happy_closed else 1.35 if mode in ('shrug', 'plz') else .12 if (t + 2) % 4.2 < .12 else .25 if mode == 'cry' else .42 if mode in ('sad', 'high', 'hippi', 'ninja', 'hah') else .75 if mode == 'sorry' else .7 - .28 * scowl if mode == 'angry' else 1 - .35 * goth_glance if mode == 'goth' else 1)
                    if eye.startswith('Eye white'):
                        if mode in ('high', 'hippi', 'drunk'):
                            node.setColorScale(1, .35 if mode in ('high', 'hippi') else .55, .35 if mode in ('high', 'hippi') else .55, 1)
                        else:
                            node.clearColorScale()
            for pupil, (x, z) in zip(pupils, pupil_origins):
                phase = (time.monotonic() - mode_start) * 5
                pupil.setX(x + .035 * math.sin(phase) if mode == 'rolleye' else x + .055 * trip_look if mode == 'trip' else x)
                pupil.setZ(z + .045 * math.cos(phase) if mode == 'rolleye' else z + .025 if mode == 'sorry' else z - .035 * goth_glance if mode == 'goth' else z)
                pupil.setSx(1 - .7 * scowl if mode == 'angry' else 1.65 if mode == 'trip' else 1)
            if blend < 1:
                for (node, prop), start_value in zip(nodes, origin):
                    target_value = getattr(node, 'get' + prop)()
                    getattr(node, 'set' + prop)(start_value + (target_value - start_value) * blend)
            index = int((time.monotonic() - speech_start) * 1000 / step_ms)
            level = envelope[index] if speaking and 0 <= index < len(envelope) else 0
            # The existing animation opens its beak around frame 7.
            tongue_out = mode == 'xd' or (mode == 'drunk' and now < tongue_until and not speaking)
            beak.pose('Duck rigAction', sleep_mouth_frame(now - mode_start) if mode == 'zzz' and not speaking else 7 if not speaking and (tongue_out or (mode == 'tired' and now < yawn_until)) else int(t * 24) % 32 if speaking and not envelope else round(level * 7))
            if not tongue_joint.isEmpty():
                tongue_joint.setY(tongue_y - .24 if tongue_out else tongue_y)
            base.graphicsEngine.renderFrame()
            texture = base.win.getScreenshot()
            data = bytes(texture.getRamImageAs('RGBA'))
            if len(data) != size * size * 4:
                raise RuntimeError(f'Unexpected duck framebuffer size: {len(data)} (expected {size * size * 4})')
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
            time.sleep(1 / fps)
    except BrokenPipeError:
        pass
    finally:
        base.destroy()


if __name__ == '__main__':
    main()
