from pathlib import Path
import tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
from astroall.camera import CanonSD,CameraError
from astroall.camera_adapters import GenericPTPSD,adapter_for
from astroall.storage import JpegCache
from astroall.session import execute,Block
from tests.test_core import FakeCamera,Widget,GP

class NikonFixture(FakeCamera):
    """Protocol fixture, not a statement of real Nikon hardware support."""
    def __init__(self):
        super().__init__()
        self.config.values['imagequality']=Widget('NEF (RAW) + JPEG Fine')
        self.config.values.pop('imageformat')
        self.config.values['shutterspeed']=Widget('1',['1','2','30','Bulb'])
        self.names=['IMG_0001.NEF','IMG_0001.JPG']
    def get_abilities(self):return SimpleNamespace(model='Nikon PTP TEST FIXTURE')

class AdapterTests(unittest.TestCase):
    def test_capture_midpoint_uses_application_utc_instead_of_bad_pc_rtc(self):
        from datetime import datetime,timezone
        camera=FakeCamera()
        with tempfile.TemporaryDirectory() as tmp,patch('astroall.timekeeping.utc_now',return_value=datetime(2026,11,9,3,tzinfo=timezone.utc)):
            result=adapter_for(camera,GP).capture_jpeg(JpegCache(tmp))
            self.assertEqual(result['approx_mid_utc'],'2026-11-09T03:00:15+00:00')
    def test_r50_keeps_exact_dedicated_adapter(self):
        self.assertIs(type(adapter_for(FakeCamera(),GP)),CanonSD)

    def test_other_brand_fixed_capture_keeps_raw_and_downloads_only_jpeg(self):
        camera=NikonFixture();adapter=adapter_for(camera,GP)
        self.assertIsInstance(adapter,GenericPTPSD)
        self.assertFalse(adapter.inspect()['bulb_supported'])
        with tempfile.TemporaryDirectory() as tmp:
            result=adapter.capture_jpeg(JpegCache(tmp),exposure=1)
            self.assertEqual(result['sd_raw'],'IMG_0001.NEF')
            self.assertEqual(camera.downloads,['IMG_0001.JPG'])
            self.assertEqual(camera.captures,1)
            self.assertFalse(list(Path(tmp).glob('*.NEF')))

    def test_other_brand_bulb_and_unknown_sd_never_trigger(self):
        camera=NikonFixture();adapter=adapter_for(camera,GP)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(CameraError,'Bulb'):adapter.capture_jpeg(JpegCache(tmp),exposure=60)
            self.assertEqual(camera.captures,0)
            camera.config.values['capturetarget'].choices=['0','1']
            with self.assertRaisesRegex(CameraError,'destino seguro'):adapter.capture_jpeg(JpegCache(tmp),exposure=1)
            self.assertEqual(camera.captures,0)

    def test_basic_session_needs_no_guide_camera_phd2_or_autofocus(self):
        camera=FakeCamera();adapter=adapter_for(camera,GP)
        with tempfile.TemporaryDirectory() as tmp,patch('astroall.guiding.PHD2Client') as phd:
            result=execute([Block(2,1,delay=0)],guide=False,capture=lambda cache,exposure,iso,stop:adapter.capture_jpeg(JpegCache(tmp)),state_file=Path(tmp)/'state.json')
            self.assertEqual(result['completed'],2);self.assertEqual(camera.captures,2)
            phd.assert_not_called()
            # FakeCamera has no autofocus controls: the working basic path
            # must not require or attempt any autofocus operation.

if __name__=='__main__':unittest.main()
