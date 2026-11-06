"""Build Mira's small animated duck as a self-contained GLB with Blender."""
import math
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    return mat


yellow = material('Duck yellow', (1.0, 0.72, 0.08))
orange = material('Beak orange', (1.0, 0.28, 0.025))
pink = material('Tongue', (0.95, 0.16, 0.25))
white = material('Eye white', (0.95, 0.97, 1.0))
black = material('Pupils', (0.015, 0.02, 0.035))


def ellipsoid(name, center, scale, mat, bone=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = True
    if bone:
        group = obj.vertex_groups.new(name=bone)
        group.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
        modifier = obj.modifiers.new('Duck rig', 'ARMATURE')
        modifier.object = rig
        obj.parent = rig
    return obj


# Face points toward negative Y; Z is up.
ellipsoid('Body', (0, 0, 0.72), (.68, .82, .61), yellow)
ellipsoid('Head', (0, -.32, 1.44), (.49, .47, .47), yellow)
ellipsoid('Wing L', (-.59, .05, .82), (.18, .42, .29), yellow)
ellipsoid('Wing R', (.59, .05, .82), (.18, .42, .29), yellow)
for side in (-1, 1):
    ellipsoid('Eye white', (side * .22, -.71, 1.59), (.12, .08, .15), white)
    ellipsoid('Pupil', (side * .22, -.778, 1.59), (.052, .032, .069), black)
    ellipsoid('Foot', (side * .31, -.21, .16), (.2, .32, .09), orange)

armature = bpy.data.armatures.new('Duck joints')
rig = bpy.data.objects.new('Duck rig', armature)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name, head in [('UpperBeak', (0, -.67, 1.35)),
                   ('LowerBeak', (0, -.67, 1.30)),
                   ('Tongue', (0, -.75, 1.30))]:
    bone = armature.edit_bones.new(name)
    bone.head = head
    bone.tail = (head[0], head[1], head[2] + .15)
armature.edit_bones['Tongue'].parent = armature.edit_bones['LowerBeak']
bpy.ops.object.mode_set(mode='OBJECT')

ellipsoid('Upper beak', (0, -.91, 1.35), (.30, .35, .09), orange, 'UpperBeak')
ellipsoid('Lower beak', (0, -.90, 1.27), (.28, .32, .065), orange, 'LowerBeak')
ellipsoid('Tongue mesh', (0, -.94, 1.32), (.13, .18, .025), pink, 'Tongue')

for frame, upper, lower, tongue in [(1, 0, 0, 0), (7, -8, 20, -10),
                                    (13, -2, 5, 5), (19, -7, 18, -8), (25, 0, 0, 0)]:
    for name, degrees in [('UpperBeak', upper), ('LowerBeak', lower), ('Tongue', tongue)]:
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler.x = math.radians(degrees)
        bone.keyframe_insert(data_path='rotation_euler', frame=frame, group=name)

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 25
bpy.context.scene.render.fps = 24
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'mira-duck.blend'))
bpy.ops.export_scene.gltf(filepath=str(ROOT / 'mira-duck.glb'), export_format='GLB',
                          export_animations=True)
