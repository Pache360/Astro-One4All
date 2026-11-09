import importlib.util
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch,MagicMock
from astroall.awake import screen_state,apply
from astroall.camera import CanonSD,CameraError

class Power0312Tests(unittest.TestCase):
    def test_live_policy_preserves_other_startup_and_can_be_reapplied(self):
        spec=importlib.util.spec_from_file_location('power_policy',Path(__file__).resolve().parents[1]/'system/power_policy.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'home/astro/.config/lxsession/LXDE/autostart';path.parent.mkdir(parents=True)
            original='@lxpanel --profile LXDE\n@xscreensaver -no-splash\n@pcmanfm --desktop\n';path.write_text(original)
            def write(path,text,mode):path.write_text(text);path.chmod(mode)
            module.install(root,write);module.install(root,write)
            self.assertEqual(path.read_text(),'@lxpanel --profile LXDE\n@pcmanfm --desktop\n')
            self.assertEqual(path.with_name(path.name+'.before-astroall0312').read_text(),original)
            self.assertIn('AllowSuspend=no',(root/'etc/systemd/sleep.conf.d/90-astroall-awake.conf').read_text())
    def test_screen_state_does_not_claim_protection_with_active_blanking(self):
        self.assertFalse(screen_state(600,True,True)['screen_kept_on'])
        self.assertTrue(screen_state(0,True,False)['screen_kept_on'])
        self.assertTrue(screen_state(0,False,False)['screen_kept_on'])
    def test_non_live_system_is_not_modified(self):
        with patch('astroall.awake.live',return_value=False),patch('astroall.awake._run') as run:
            self.assertFalse(apply()['applied']);run.assert_not_called()
    def test_capture_busy_is_not_retried_and_uses_native_context(self):
        class BusyError(Exception):code=-110
        camera=MagicMock();camera.capture.side_effect=BusyError('[-110] I/O in progress');report=MagicMock()
        adapter=CanonSD(camera,SimpleNamespace(GP_CAPTURE_IMAGE=0),report);adapter.context=object()
        with self.assertRaisesRegex(CameraError,'sin repetir'):adapter.capture_fixed()
        camera.capture.assert_called_once_with(0,adapter.context)
        self.assertTrue(report.update.call_args.kwargs['uncertain_photo'])
