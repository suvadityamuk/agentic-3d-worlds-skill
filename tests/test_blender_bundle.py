"""Scope/format guards; real Blender execution is also checked in integration."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'share-3d-world-agent-run/scripts'))
import blender_bundle as b
from PIL import Image

class BlenderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.run=Path(self.temp.name);self.root=self.run/'artifacts';self.root.mkdir()
        (self.root/'create.py').write_text('import bpy\nbpy.ops.mesh.primitive_cube_add()\n')
        (self.root/'scene.blend').write_bytes(b'BLENDER-test')
        Image.new('RGB',(64,64),'blue').save(self.root/'preview.png')
        self.doc={'asset':{'version':'2.0'},'meshes':[{'primitives':[{'attributes':{'POSITION':0}}]}], 'nodes':[{'mesh':0}],'scenes':[{'nodes':[0]}]}
        self.glb()
        self.trace={'steps':[{'type':'tool_call','name':'blender','input':'create.py'}]}
        self.addCleanup(patch.stopall)
        patch.dict('os.environ',{'BLENDER_EXECUTABLE':'test-blender'}).start()
        self.proc=patch.object(b.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'BLENDER_PUBLIC_STRINGS=[]\nBLENDER_CHECK_OK')).start()
    def glb(self):
        raw=json.dumps(self.doc).encode();raw+=b' '*((-len(raw))%4)
        body=struct.pack('<II',len(raw),0x4E4F534A)+raw+struct.pack('<II',4,0x004E4942)+b'\0'*4
        (self.root/'model.glb').write_bytes(struct.pack('<4sII',b'glTF',2,len(body)+12)+body)
    def test_missing_blend_rejected_before_execution(self):
        (self.root/'scene.blend').unlink()
        with self.assertRaisesRegex(ValueError,'require'):b.validate_blender(self.run,self.trace)
        self.proc.assert_not_called()
    def test_web_code_rejected_even_with_blender_files(self):
        (self.root/'world.ts').write_text("import * as THREE from 'three'")
        with self.assertRaisesRegex(ValueError,'web projects'):b.validate_blender(self.run,self.trace)
    def test_export_only_script_rejected(self):
        (self.root/'create.py').write_text("import bpy\nbpy.ops.export_scene.gltf(filepath='model.glb')\n")
        with self.assertRaisesRegex(ValueError,'modeling'):b.validate_blender(self.run,self.trace)
    def test_missing_execution_evidence_rejected(self):
        with self.assertRaisesRegex(ValueError,'evidence'):b.validate_blender(self.run,{'steps':[]})
    def test_invalid_and_external_glb_rejected(self):
        (self.root/'model.glb').write_bytes(b'not a model')
        with self.assertRaisesRegex(ValueError,'GLB'):b.validate_blender(self.run,self.trace)
        self.doc['buffers']=[{'uri':'remote.bin'}];self.glb()
        with self.assertRaisesRegex(ValueError,'embedded'):b.validate_blender(self.run,self.trace)
    def test_glb_identity_metadata_rejected(self):
        self.doc['nodes'][0]['name']='11111111-2222-3333-4444-555555555555';self.glb()
        with self.assertRaisesRegex(ValueError,'identifying'):b.validate_blender(self.run,self.trace)
    def test_blender_failure_cannot_pass(self):
        self.proc.return_value.returncode=1
        with self.assertRaisesRegex(ValueError,'could not verify'):b.validate_blender(self.run,self.trace)
    def test_autoexec_disabled_and_geometry_check_required(self):
        b.validate_blender(self.run,self.trace)
        self.assertIn('--disable-autoexec',self.proc.call_args.args[0])
        self.assertIn('--python-exit-code',self.proc.call_args.args[0])
    def test_blender_embedded_private_path_rejected(self):
        self.proc.return_value.stdout=b'BLENDER_PUBLIC_STRINGS=["/Users/alice/private.png"]\nBLENDER_CHECK_OK'
        with self.assertRaisesRegex(ValueError,'private data'):b.validate_blender(self.run,self.trace)
    def test_mesh_table_binds_exact_bytes_and_metadata(self):
        (self.run/'trace.json').write_text(json.dumps(self.trace))
        (self.run/'metadata.json').write_text(json.dumps({'title':'Rounded Block'}))
        b.write_viewer(self.run);b.validate_viewer(self.run)
        (self.root/'model.glb').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'exact reviewed'):b.validate_viewer(self.run)

if __name__=='__main__':unittest.main()
