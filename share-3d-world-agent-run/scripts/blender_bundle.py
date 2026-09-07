"""Blender eligibility and native Hugging Face Mesh table validation."""
import ast
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

REQUIRED = {'scene.blend', 'create.py', 'model.glb', 'preview.png'}
ALLOWED = {'.blend', '.py', '.glb', '.png', '.jpg', '.jpeg', '.webp', '.json', '.md', '.txt'}
NATIVE_FEATURES = {'title': {'dtype':'string','_type':'Value'},
            'mesh': {'_type':'Mesh'}, 'preview': {'_type':'Image'},
            'trace': {'dtype':'string','_type':'Value'},
            'metadata': {'dtype':'string','_type':'Value'}}


def arrow_schema(native=False):
    import pyarrow as pa
    media = pa.struct([('bytes',pa.binary()),('path',pa.string())])
    features = dict(NATIVE_FEATURES)
    if not native:
        del features['mesh']
        features['glb']={'dtype':'string','_type':'Value'}
    return pa.schema([('title',pa.string()),('mesh',media) if native else ('glb',pa.string()),
                      ('preview',media),('trace',pa.string()),('metadata',pa.string())],
                     metadata={b'huggingface':json.dumps({'info':{'features':features}}).encode()})


def viewer_row(run, native=False):
    row = {'title':json.loads((run/'metadata.json').read_text())['title'],
           'preview':{'bytes':(run/'artifacts/preview.png').read_bytes(),'path':'preview.png'},
           'trace':(run/'trace.json').read_text(), 'metadata':(run/'metadata.json').read_text()}
    if native:
        row['mesh']={'bytes':(run/'artifacts/model.glb').read_bytes(),'path':'model.glb'}
    else:
        row['glb']='runs/'+run.name+'/artifacts/model.glb'
    return row


def write_viewer(run):
    import pyarrow as pa
    import pyarrow.parquet as pq
    for native, name in [(False,'viewer.parquet'),(True,'mesh.parquet')]:
        pq.write_table(pa.Table.from_pylist([viewer_row(run,native)],schema=arrow_schema(native)), run/name)


def validate_viewer(run):
    import pyarrow.parquet as pq
    for native, name in [(False,'viewer.parquet'),(True,'mesh.parquet')]:
        table=pq.read_table(run/name)
        if not table.schema.equals(arrow_schema(native),check_metadata=True) or table.to_pylist()!=[viewer_row(run,native)]:
            raise ValueError('Viewer tables must contain the exact reviewed GLB, preview and trace with correct feature metadata')


def validate_glb(path, private_terms=()):
    data=path.read_bytes()
    if len(data)<20 or struct.unpack_from('<4sII',data)!= (b'glTF',2,len(data)):
        raise ValueError('Expected a valid GLB 2.0 container')
    chunks=[]; offset=12
    while offset<len(data):
        if offset+8>len(data): raise ValueError('Truncated GLB chunk')
        size,kind=struct.unpack_from('<II',data,offset);offset+=8
        if size%4 or offset+size>len(data): raise ValueError('Invalid GLB chunk length')
        chunks.append((kind,data[offset:offset+size]));offset+=size
    if [c[0] for c in chunks] != [0x4E4F534A,0x004E4942]:
        raise ValueError('GLB must have JSON and embedded binary chunks')
    doc=json.loads(chunks[0][1])
    if doc.get('asset',{}).get('version')!='2.0':
        raise ValueError('GLB asset must use glTF 2.0')
    if not doc.get('meshes') or not doc.get('scenes') or not doc.get('nodes'):
        raise ValueError('GLB has no scene geometry')
    if doc.get('extensionsRequired'):
        raise ValueError('Use core glTF materials/geometry without required decoder extensions')
    if any('uri' in item for key in ['buffers','images'] for item in doc.get(key,[])):
        raise ValueError('GLB buffers and textures must be embedded, with no external URIs')
    # Names/extras can disclose identifiers even when the mesh is binary.
    from privacy import clean_object
    from contribute import redact_obj
    if clean_object(doc, private_terms)[1] or redact_obj(doc)[1]:
        raise ValueError('GLB JSON contains identifying data or credentials; sanitize in Blender and export again')
    return doc


def validate_blender(run, trace, private_terms=()):
    root=run/'artifacts'
    if not all((root/name).is_file() for name in REQUIRED):
        raise ValueError('Blender contributions require artifacts/scene.blend, create.py, model.glb and preview.png')
    for p in root.rglob('*'):
        if not p.is_file(): continue
        if p.suffix.lower() not in ALLOWED or p.name in {'package.json','package-lock.json','tsconfig.json'}:
            raise ValueError('Only Blender source, assets and documentation are allowed; web projects and archives are excluded')
        if p.suffix.lower() in {'.blend','.glb'} and p.name not in {'scene.blend','model.glb'}:
            raise ValueError('Only the validated canonical Blender scene and GLB are accepted')
        if p.suffix=='.py':
            tree=ast.parse(p.read_text())
            if any(isinstance(n,ast.Constant) and isinstance(n.value,str) and ('three.js' in n.value.lower() or '@react-three/' in n.value) for n in ast.walk(tree)):
                raise ValueError('Three.js artifacts are not eligible')
    source=(root/'create.py').read_text();tree=ast.parse(source)
    if not any(isinstance(n,ast.Import) and any(a.name=='bpy' for a in n.names) or isinstance(n,ast.ImportFrom) and n.module=='bpy' for n in ast.walk(tree)):
        raise ValueError('create.py must use bpy to create the scene')
    if not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and (ast.unparse(n.func).startswith('bpy.ops.mesh.') or ast.unparse(n.func).startswith('bpy.data.') or ast.unparse(n.func).startswith('bpy.ops.object.') or ast.unparse(n.func).startswith('bpy.ops.curve.')) for n in ast.walk(tree)):
        raise ValueError('create.py must contain Blender modeling operations, not just import/export')
    calls=[s for s in trace['steps'] if s.get('type')=='tool_call']
    if not any('blender' in json.dumps(s).lower() or 'bpy' in json.dumps(s).lower() for s in calls):
        raise ValueError('Observable Blender/bpy execution evidence is required')
    if not (root/'scene.blend').read_bytes().startswith(b'BLENDER'):
        raise ValueError('Save scene.blend uncompressed for inspectable Blender validation')
    validate_glb(root/'model.glb', private_terms)
    from PIL import Image
    with Image.open(root/'preview.png') as im:
        if im.format!='PNG' or min(im.size)<64: raise ValueError('A rendered PNG preview of at least 64 pixels per side is required')
        im.verify()
    blender=os.environ.get('BLENDER_EXECUTABLE') or shutil.which('blender')
    if not blender and Path('/Applications/Blender.app/Contents/MacOS/Blender').is_file():
        blender='/Applications/Blender.app/Contents/MacOS/Blender'
    if not blender: raise ValueError('Blender must be available to verify the scene and GLB; retain the bundle')
    result=subprocess.run([blender,'--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',str(Path(__file__).with_name('blender_check.py')),'--',str(root.resolve())],capture_output=True,timeout=180)
    if result.returncode or b'BLENDER_CHECK_OK' not in result.stdout:
        raise ValueError('Blender could not verify the saved scene against its GLB; inspect locally and repair before sharing')

    from privacy import clean_text
    from contribute import redact_text
    lines=result.stdout.decode('utf-8',errors='replace').splitlines()
    reports=[line.split('=',1)[1] for line in lines if line.startswith('BLENDER_PUBLIC_STRINGS=')]
    if len(reports)!=1:
        raise ValueError('Blender privacy inspection did not complete')
    for value in json.loads(reports[0]):
        if clean_text(value,private_terms)[1] or redact_text(value)[1]:
            raise ValueError('Blender names, properties, embedded text or paths contain private data; sanitize the scene first')
