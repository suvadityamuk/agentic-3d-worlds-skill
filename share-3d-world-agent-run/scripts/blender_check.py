"""Run inside Blender with auto-execution disabled; never execute embedded scripts."""
import bpy
import json
import math
import sys
from pathlib import Path


def geometry():
    deps = bpy.context.evaluated_depsgraph_get()
    vertices = []
    faces = 0
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            faces += len(mesh.loop_triangles)
            vertices.extend(tuple(evaluated.matrix_world @ v.co) for v in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    if not vertices or not faces or not all(math.isfinite(x) for v in vertices for x in v):
        raise ValueError('Scene must contain finite visible mesh geometry')
    return {'triangles': faces, 'bounds': [[min(v[i] for v in vertices), max(v[i] for v in vertices)] for i in range(3)]}


def main():
    root = Path(sys.argv[sys.argv.index('--') + 1])
    bpy.ops.wm.open_mainfile(filepath=str(root/'scene.blend'), load_ui=False, use_scripts=False)
    # External libraries/assets make the exported example non-portable.
    if bpy.data.libraries:
        raise ValueError('Linked libraries must be made local')
    if any(i.source == 'FILE' and i.filepath and not i.packed_file for i in bpy.data.images):
        raise ValueError('Textures must be packed into the Blender file')
    public_strings=[]
    for collection in ['objects','meshes','materials','images','textures','collections','scenes','worlds','cameras','lights','texts']:
        for block in getattr(bpy.data,collection):
            public_strings.append(block.name)
            for key in block.keys():
                public_strings.extend([key,str(block[key])])
    public_strings.extend(text.as_string() for text in bpy.data.texts)
    public_strings.extend(image.filepath for image in bpy.data.images)
    public_strings.append(bpy.context.scene.render.filepath)
    print('BLENDER_PUBLIC_STRINGS='+json.dumps(public_strings))
    original = geometry()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(root/'model.glb'))
    exported = geometry()
    if original['triangles'] != exported['triangles']:
        raise ValueError('GLB triangle count differs from the visible Blender meshes')
    scale = max(1., *(abs(x) for b in original['bounds'] for x in b))
    if any(abs(a-b) > scale*0.0001 for ba,bb in zip(original['bounds'],exported['bounds']) for a,b in zip(ba,bb)):
        raise ValueError('GLB bounds differ from the Blender scene')
    print('BLENDER_CHECK_OK')

if __name__ == '__main__':
    main()
