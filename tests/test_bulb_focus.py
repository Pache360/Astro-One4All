from pathlib import Path
from types import SimpleNamespace
import copy
import json
import tempfile
import unittest
from test_core import FakeCamera,Widget
from astroall.camera import CanonSD,CameraError
from astroall.storage import JpegCache
from astroall.focus import measure

GP=SimpleNamespace(GP_CAPTURE_IMAGE=0,GP_FILE_TYPE_NORMAL=1,GP_EVENT_TIMEOUT=2,GP_EVENT_FILE_ADDED=3)
class StopAfterPress:
    def __init__(self): self.calls=0
    def is_set(self): self.calls+=1;return self.calls>1
    def wait(self,timeout): return True
class BulbCamera(FakeCamera):
    def __init__(self):
        super().__init__();self.actions=[];self.fail_release=False
        self.config.values.update(shutterspeed=Widget('30',['1','2','30','Bulb']),iso=Widget('800',['100','800']),eosremoterelease=Widget('None',['None','Press Full','Release Full']))
    def get_config(self): return copy.deepcopy(self.config)
    def set_config(self,config):
        value=config.values['eosremoterelease'].value
        if value!='None':
            self.actions.append(value);config.values['eosremoterelease'].value='None'
            if value=='Release Full' and self.fail_release: raise RuntimeError('USB disconnected')
        self.config=config
    def wait_for_event(self,timeout):
        if 'Release Full' in self.actions: return GP.GP_EVENT_FILE_ADDED,SimpleNamespace(folder='/store_00010001/DCIM/100CANON',name='IMG_0001.JPG')
        return GP.GP_EVENT_TIMEOUT,None

class BulbTests(unittest.TestCase):
    def test_cancel_closes_bulb_and_downloads_only_matching_jpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            camera=BulbCamera();result=CanonSD(camera,GP).capture_jpeg(JpegCache(tmp),exposure=60,iso='800',stop=StopAfterPress())
            self.assertEqual(camera.actions,['Press Full','Release Full']);self.assertTrue(result['interrupted']);self.assertTrue(result['bulb'])
            self.assertEqual(camera.captures,0);self.assertEqual(camera.downloads,['IMG_0001.JPG'])
    def test_no_bulb_pair_means_no_open_shutter(self):
        with tempfile.TemporaryDirectory() as tmp:
            camera=BulbCamera();camera.config.values['eosremoterelease'].choices=['None','Press Full']
            with self.assertRaises(CameraError): CanonSD(camera,GP).capture_jpeg(JpegCache(tmp),exposure=60)
            self.assertFalse(camera.actions)
    def test_release_failure_is_explicit_and_not_retried_as_an_exposure(self):
        with tempfile.TemporaryDirectory() as tmp:
            camera=BulbCamera();camera.fail_release=True
            with self.assertRaisesRegex(CameraError,'cerrar Bulb'): CanonSD(camera,GP).capture_jpeg(JpegCache(tmp),exposure=60,stop=StopAfterPress())
            self.assertEqual(camera.actions,['Press Full','Release Full']);self.assertFalse(camera.downloads)
    def test_fixed_exposure_and_iso_are_named_and_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            camera=BulbCamera();result=CanonSD(camera,GP).capture_jpeg(JpegCache(tmp),exposure=2,iso='100')
            self.assertEqual(result['exposure_seconds'],2);self.assertEqual(camera.config.values['iso'].value,'100');self.assertEqual(camera.captures,1)


class SingleConfigCamera(BulbCamera):
    """Detached widgets like SWIG; refuses configuration reads during exposure."""
    def __init__(self):
        super().__init__();self.open=False;self.polls=0;self.fail_poll=False;self.fail_press=False;self.early=False
    def get_config(self):
        if self.open: raise AssertionError('get_config during open Bulb')
        return self.config
    def get_single_config(self,name):
        if self.open: raise AssertionError('get_single_config during open Bulb')
        return copy.deepcopy(self.config.values[name])
    def set_single_config(self,name,widget):
        if name!='eosremoterelease': self.config.values[name]=copy.deepcopy(widget);return
        value=widget.get_value();self.actions.append(value)
        if value.startswith('Press'):
            self.open=True
            if self.fail_press: raise RuntimeError('press failed after USB send')
        else: self.open=False
    def wait_for_event(self,timeout):
        if self.open:
            self.polls+=1
            if self.fail_poll: raise RuntimeError('event I/O error')
            if self.early: return GP.GP_EVENT_FILE_ADDED,SimpleNamespace(folder='/store_00010001/DCIM/100CANON',name='IMG_0001.JPG')
        if not self.open and any(x.startswith('Release') for x in self.actions):
            return GP.GP_EVENT_FILE_ADDED,SimpleNamespace(folder='/store_00010001/DCIM/100CANON',name='IMG_0001.JPG')
        return super().wait_for_event(timeout)


class CanonRegressionTests(unittest.TestCase):
    def test_actual_2533_and_newer_command_names_are_sent_verbatim(self):
        for names in [('Press Full','Release Full'),('Press Full MF','Release')]:
            with self.subTest(names=names),tempfile.TemporaryDirectory() as tmp:
                camera=SingleConfigCamera();camera.config.values['eosremoterelease'].choices=['None',*names]
                result=CanonSD(camera,GP).capture_jpeg(JpegCache(tmp),exposure=3,force_bulb=True,stop=StopAfterPress())
                self.assertEqual(camera.actions,list(names));self.assertFalse(camera.open)
                self.assertEqual(camera.downloads,['IMG_0001.JPG']);self.assertTrue(result['bulb'])
    def test_event_or_press_error_still_sends_release_without_config_read(self):
        for failure in ('fail_poll','fail_press'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
                camera=SingleConfigCamera();setattr(camera,failure,True)
                with self.assertRaisesRegex(RuntimeError,'error|failed'):
                    CanonSD(camera,GP).capture_jpeg(JpegCache(tmp),exposure=3,force_bulb=True)
                self.assertEqual(camera.actions,['Press Full','Release Full']);self.assertFalse(camera.open)
                self.assertFalse(camera.downloads)
    def test_full_duration_polls_events_and_closes_once(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            camera=SingleConfigCamera();clock=[0.]
            def monotonic(): clock[0]+=.05;return clock[0]
            with patch('astroall.camera.time.monotonic',side_effect=monotonic):
                result=CanonSD(camera,GP).capture_jpeg(JpegCache(tmp),exposure=3,force_bulb=True)
            self.assertGreater(camera.polls,10);self.assertGreaterEqual(result['exposure_seconds'],3)
            self.assertEqual(camera.actions,['Press Full','Release Full']);self.assertFalse(camera.open)
    def test_premature_file_stops_plan_after_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            camera=SingleConfigCamera();camera.early=True
            with self.assertRaisesRegex(CameraError,'antes de la duración'):
                CanonSD(camera,GP).capture_jpeg(JpegCache(tmp),exposure=3,force_bulb=True)
            self.assertFalse(camera.open);self.assertEqual(camera.actions,['Press Full','Release Full'])
    def test_bad_manual_mode_does_not_modify_iso_or_open_shutter(self):
        with tempfile.TemporaryDirectory() as tmp:
            camera=SingleConfigCamera();camera.config.values['autoexposuremode'].value='Auto'
            with self.assertRaisesRegex(CameraError,'modo M'):
                CanonSD(camera,GP).capture_jpeg(JpegCache(tmp),exposure=60,iso='100')
            self.assertEqual(camera.config.values['iso'].value,'800');self.assertFalse(camera.actions)
    def test_failure_report_keeps_stage_and_version_without_images(self):
        from astroall.camera_diagnostic import CaptureReport
        with tempfile.TemporaryDirectory() as tmp:
            report=CaptureReport(Path(tmp)/'diagnostic.json',exposure_seconds=60)
            report.update('opening_bulb');report.failed(RuntimeError('USB busy'))
            value=json.loads(report.path.read_text(encoding='utf-8'))
            self.assertEqual(value['failed_stage'],'opening_bulb');self.assertEqual(value['error'],'USB busy')
        from astroall import __version__
        self.assertEqual(value['application_version'],__version__)

    def test_borrowed_choice_iterator_keeps_its_owner_alive(self):
        import weakref
        class BorrowedChoices:
            def __init__(self,owner): self.owner=weakref.ref(owner);self.index=0
            def __iter__(self): return self
            def __next__(self):
                owner=self.owner()
                if owner is None: raise RuntimeError('[-2] Bad parameters: freed native widget')
                if self.index==len(owner.choices): raise StopIteration
                value=owner.choices[self.index];self.index+=1;return value
        class BorrowedWidget(Widget):
            def get_choices(self): return BorrowedChoices(self)
        camera=SingleConfigCamera()
        for name in ('shutterspeed','eosremoterelease'):
            current=camera.config.values[name]
            camera.config.values[name]=BorrowedWidget(current.value,current.choices)
        adapter=CanonSD(camera,GP)
        self.assertEqual(adapter.configure_exposure(2),(2,False))
        self.assertEqual(adapter.release_pair(),('Press Full','Release Full'))

class FocusTests(unittest.TestCase):
    def test_synthetic_stars_get_larger_hfr_when_defocused(self):
        try: import numpy as np
        except ImportError: self.skipTest('NumPy is included in the Live image')
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            yy,xx=np.mgrid[:400,:600];values=[]
            for sigma in (1.8,3.2):
                image=np.full((400,600),12.)
                for x,y in [(70,60),(170,60),(320,90),(480,90),(85,250),(230,260),(390,280),(520,270)]: image+=160*np.exp(-((xx-x)**2+(yy-y)**2)/(2*sigma**2))
                path=Path(tmp)/f'{sigma}.jpg';Image.fromarray(np.uint8(np.clip(image,0,255))).save(path,quality=98)
                values.append(measure(path))
            self.assertGreaterEqual(values[0]['stars'],6);self.assertGreater(values[1]['hfr_original_px'],values[0]['hfr_original_px']*1.3)
