from pathlib import Path
from types import SimpleNamespace
import tempfile,unittest
from unittest.mock import MagicMock,patch
from astroall.equipment import apply_camera_selection,save,load

class EquipmentTests(unittest.TestCase):
    def test_selected_camera_uses_exact_usb_model_and_port_and_never_falls_back(self):
        gp=MagicMock();gp.Camera.autodetect.return_value=[('Canon EOS R50','usb:001,005'),('Nikon TEST','usb:001,006')]
        camera=MagicMock();settings={'main_model':'Nikon TEST','main_port':'usb:001,006'}
        apply_camera_selection(camera,gp,settings)
        gp.PortInfoList().lookup_path.assert_called_once_with('usb:001,006')
        gp.CameraAbilitiesList().lookup_model.assert_called_once_with('Nikon TEST')
        camera.set_port_info.assert_called_once();camera.set_abilities.assert_called_once()
        camera.reset_mock()
        moved=apply_camera_selection(camera,gp,dict(settings,main_port='usb:001,009'))
        self.assertTrue(moved['port_changed'])
        camera.reset_mock()
        with self.assertRaisesRegex(RuntimeError,'no se usó otra'):apply_camera_selection(camera,gp,dict(settings,main_model='Other camera'))
        camera.set_port_info.assert_not_called()

    def test_manual_focus_and_optional_guide_persist_without_device_operations(self):
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)):
            value=save({'main_model':'Canon EOS R50','main_port':'usb:001,005','guide_enabled':False,'guide_path':''})
            self.assertEqual(load(),value);self.assertEqual(load()['focus'],'manual')
            with self.assertRaises(ValueError):save(dict(value,main_port='other-device'))
