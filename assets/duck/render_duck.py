"""Render transparent, lightweight duck poses from the editable 3D rig."""
from pathlib import Path
import bpy
from mathutils import Vector

root = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root / 'mira-duck.blend'))
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.render.film_transparent = True
scene.render.resolution_x = 384
scene.render.resolution_y = 384
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
camera_data = bpy.data.cameras.new('Overlay camera')
camera = bpy.data.objects.new('Overlay camera', camera_data)
scene.collection.objects.link(camera)
camera.location = (2.8, -6.0, 2.5)
direction = Vector((0, -.10, 1.05)) - camera.location
camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 2.65
scene.camera = camera
for frame, name in [(1, 'duck-closed.png'), (7, 'duck-open.png')]:
    scene.frame_set(frame)
    scene.render.filepath = str(root / name)
    bpy.ops.render.render(write_still=True)
