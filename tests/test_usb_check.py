"""Connection-only helper preserves the driver reason and never requests a photo."""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name=='posix','Linux USB helper')
class USBCheckTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('canon_check',Path(__file__).resolve().parents[1]/'system/canon-usb-check.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
    def fake(self,fail=False,detected=True):
        class Context:
            def set_error_func(self,callback,data): self.callback=callback
            def set_status_func(self,callback,data): pass
        class List:
            def load(self,*args): pass
            def lookup_model(self,*args): return 0
            def lookup_path(self,*args): return 0
            def __getitem__(self,key): return object()
        class Camera:
            captures=0
            @staticmethod
            def autodetect(context): return [('Canon EOS R50','usb:001,003')] if detected else []
            def set_abilities(self,*args): pass
            def set_port_info(self,*args): pass
            def init(self,context):
                if fail:
                    context.callback(context,'PTP: Session Already Open',None)
                    raise RuntimeError('[-1] Unspecified error')
            def get_single_config(self,name,*args): return SimpleNamespace(get_value=lambda:'test')
            def exit(self,*args): pass
            def capture(self,*args): Camera.captures+=1;raise AssertionError('No photos permitted')
        return SimpleNamespace(Context=Context,Camera=Camera,CameraAbilitiesList=List,PortInfoList=List,gp_library_version=lambda _:['2.5.33'])
    def test_unspecified_error_keeps_the_underlying_ptp_message(self):
        gp=self.fake(fail=True)
        with tempfile.TemporaryDirectory() as tmp,patch.object(self.module.subprocess,'run',return_value=SimpleNamespace(stdout='',stderr='')):
            result,path=self.module.run(gp,tmp)
            self.assertEqual(result['error'],'[-1] Unspecified error');self.assertIn('Session Already Open',result['driver_messages'][0])
            self.assertEqual(result['failed_stage'],'initializing_usb');self.assertTrue(path.exists())
            self.assertEqual(gp.Camera.captures,0)
    def test_success_only_reads_settings(self):
        gp=self.fake()
        with tempfile.TemporaryDirectory() as tmp,patch.object(self.module.subprocess,'run',return_value=SimpleNamespace(stdout='',stderr='')):
            result,path=self.module.run(gp,tmp)
            self.assertEqual(result['result'],'connection_ok');self.assertEqual(result['photos_requested'],0)
            self.assertEqual(gp.Camera.captures,0)
    def test_absent_r50_does_not_open_another_camera(self):
        gp=self.fake(detected=False)
        with tempfile.TemporaryDirectory() as tmp:
            result,path=self.module.run(gp,tmp)
            self.assertEqual(result['result'],'failed');self.assertEqual(result['failed_stage'],'detecting_usb')
            self.assertEqual(gp.Camera.captures,0)
