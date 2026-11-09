from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
import tempfile,unittest
from unittest.mock import patch,MagicMock
from astroall.catalog import Target
from astroall.recommendations import capture_proposal
from astroall.preferences import load,save
from astroall.session import recenter,execute,Block
from astroall.solve import Position
from astroall.equipment import apply_camera_selection

class Workflow039Tests(unittest.TestCase):
    def test_changing_focal_changes_plan_exposure_field_and_count(self):
        target=Target('x','X',10,20,major_arcmin=120,minor_arcmin=60)
        a=capture_proposal(target,'APS-C Canon',50);b=capture_proposal(target,'APS-C Canon',250)
        self.assertEqual(a['recommended_focal'],b['recommended_focal'])
        self.assertGreater(a['exposure'],b['exposure']);self.assertGreater(a['field_w'],b['field_w'])
        self.assertGreater(b['count'],a['count'])
    def test_preferences_validate_and_persist(self):
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)):
            value=save(dict(load(),focal=100,jpg_every=5));self.assertEqual(load(),value)
            for name,bad in [('focal',float('nan')),('jpg_every',0),('jpg_exposure',60)]:
                with self.assertRaises(ValueError):save(dict(value,**{name:bad}))
    def test_existing_exposure_jpg_is_solved_without_extra_capture_if_centered(self):
        target=Target('x','X',10,20);client=MagicMock();client.__enter__.return_value=client
        capture=MagicMock(side_effect=AssertionError('No extra exposure needed'))
        with patch('astroall.session.load_settings',return_value={'latitude':17,'longitude':-96,'clock_confirmed':True}),patch('astroall.session.visibility',return_value={'alt_deg':50}):
            result=recenter(target,5,first_shot={'jpeg':'last-exposure.jpg'},capture=capture,solver=lambda *_:Position(10,20),client_factory=lambda:client)
        self.assertTrue(result['centered']);capture.assert_not_called();client.goto_eod.assert_not_called()
    def test_sequence_reuses_its_last_jpg_for_periodic_correction_without_phd(self):
        target=Target('x','X',10,20);client=MagicMock();client.__enter__.return_value=client;events=[]
        with tempfile.TemporaryDirectory() as tmp,patch('astroall.session.load_settings',return_value={'latitude':17,'longitude':-96,'clock_confirmed':True}),patch('astroall.session.visibility',return_value={'alt_deg':50,'ra_hours_eod':1,'dec_deg_eod':20}),patch('astroall.session.IndiClient',return_value=client),patch('astroall.session.recenter') as center,patch('astroall.guiding.PHD2Client') as phd:
            state=execute([Block(3,1,delay=0)],targets=[target],recenter_every=2,field_deg=5,capture=lambda *_:{'jpeg':'science.jpg'},state_file=Path(tmp)/'state.json',emit=events.append)
            self.assertEqual(state['completed'],3);self.assertEqual(center.call_count,2)
            self.assertEqual(center.call_args.kwargs['first_shot']['jpeg'],'science.jpg');phd.assert_not_called()
    def test_auto_camera_selection_binds_detected_model_and_port(self):
        gp=MagicMock();gp.Camera.autodetect.return_value=[('Canon EOS R50','usb:001,007')];camera=MagicMock()
        result=apply_camera_selection(camera,gp,settings={})
        self.assertEqual(result['model'],'Canon EOS R50');camera.set_port_info.assert_called_once();camera.set_abilities.assert_called_once()
        gp.Camera.autodetect.return_value=[('Canon EOS R50','usb:001,007'),('Canon EOS R50','usb:001,008')]
        with self.assertRaises(RuntimeError):apply_camera_selection(camera,gp,settings={'main_model':'Canon EOS R50'})
