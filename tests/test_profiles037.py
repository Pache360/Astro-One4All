import tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from astroall.mount_profiles import load,create,activate
from astroall.mount_service import profile,save_profile
from astroall.timekeeping import import_mount_time,load_settings

class OATProfilesTests(unittest.TestCase):
    def test_board_profiles_keep_baud_port_and_existing_mega_configuration_separate(self):
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)):
            mega={'driver':'indi_astroall_oat','device':'Astro One4All OAT','port':'/dev/ttyUSB0','baud':'19200'}
            save_profile(mega)
            mks=dict(mega,port='/dev/ttyUSB1',baud='38400')
            key=create('OAT MKS','MKS Gen L v2.1',mks)
            self.assertEqual(profile(),mega)
            activate(key);self.assertEqual(profile(),mks)
            save_profile(dict(mks,port='/dev/ttyUSB2'))
            self.assertEqual(load()['profiles'][key]['connection']['port'],'/dev/ttyUSB2')
            activate('default');self.assertEqual(profile(),mega)
            with self.assertRaises(ValueError):create('OAT MKS','MKS Gen L v2.1',mks)

    def test_switching_board_invalidates_previous_mount_clock_anchor(self):
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)):
            import_mount_time({'UTC':'2026-11-09T03:00:00+00:00','LAT':'17','LON':'-96','MONOTONIC':str(time.monotonic())})
            cfg=profile();key=create('Sin GPS','ESP32 ESP32DEV',cfg,time_source='pc');activate(key)
            settings=load_settings();self.assertFalse(settings['clock_confirmed']);self.assertFalse(settings['use_mount_time'])
            self.assertNotIn('clock_anchor',settings)
