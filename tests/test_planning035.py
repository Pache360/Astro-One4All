from datetime import datetime,timezone
import io,json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
import xml.etree.ElementTree as ET
from astroall.catalog import Target
from astroall.mount_time import gps_sync,read_site_time,sync_site_time
from astroall.oat_driver import Driver,DEVICE
from astroall.oat_protocol import OATProtocol
from astroall.timekeeping import import_mount_time,load_settings,utc_now,boot_id,clock_snapshot
from astroall.sky import Site,visibility_label,atlas_visibility,visibility
from astroall.recommendations import recommend
from astroall.session import execute,Block
from tests.test_features03 import SerialFake

class GPSPlanningTests(unittest.TestCase):
    def test_meade_sign_date_rollover_and_getters_only(self):
        serial=SerialFake();result=read_site_time(OATProtocol(serial))
        self.assertEqual(result['UTC'],'2026-11-09T03:00:00+00:00')
        self.assertEqual(float(result['LAT']),17);self.assertEqual(float(result['LON']),-96)
        self.assertEqual(float(result['OAT_HA_HOURS']),3)
        self.assertTrue(all(cmd.startswith((':G',':XG')) for cmd in serial.commands))
        self.assertNotIn(':gT#',serial.commands)

    def test_gps_sync_is_explicit_single_char_reply(self):
        serial=SerialFake();protocol=OATProtocol(serial)
        self.assertTrue(gps_sync(protocol))
        self.assertEqual(serial.commands,[':gT30000#'])

    def test_gps_sync_then_read_marks_fresh_fix(self):
        serial=SerialFake();result=sync_site_time(OATProtocol(serial))
        self.assertEqual(result['GPS_SYNC'],'1')
        self.assertIn(':gT#',result['SOURCE'])
        self.assertEqual(float(result['LAT']),17);self.assertEqual(float(result['LON']),-96)
        self.assertEqual(serial.commands[0],':gT30000#')

    def test_gps_sync_without_fix_keeps_stored_values_and_warns(self):
        serial=SerialFake();serial.gt='0'
        result=sync_site_time(OATProtocol(serial))
        self.assertEqual(result['GPS_SYNC'],'0')
        self.assertIn('sin fix',result['SOURCE'])
        self.assertEqual(float(result['LAT']),17)

    def test_driver_gps_sync_switch_sends_gT_and_updates_site_time(self):
        serial=SerialFake();d=Driver(io.StringIO(),lambda *_:serial)
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)):
            d.process(ET.fromstring(f'<newSwitchVector device="{DEVICE}" name="CONNECTION"><oneSwitch name="CONNECT">On</oneSwitch></newSwitchVector>'))
            d.process(ET.fromstring(f'<newSwitchVector device="{DEVICE}" name="OAT_GPS_SYNC"><oneSwitch name="SYNC">On</oneSwitch></newSwitchVector>'))
        self.assertIn(':gT30000#',serial.commands)
        self.assertEqual(d.properties['OAT_SITE_TIME']['values']['GPS_SYNC'],'1')
        d.disconnect()

    def test_wrong_pc_rtc_uses_monotonic_oat_anchor_and_invalidates_on_reboot(self):
        sample={'UTC':'2026-11-09T03:00:00+00:00','LAT':'17','LON':'-96','MONOTONIC':'1000'}
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)),patch('astroall.timekeeping.time.monotonic',return_value=1002),patch('astroall.timekeeping.boot_id',return_value='boot-A'):
            saved=import_mount_time(sample)
            self.assertEqual(utc_now().isoformat(),'2026-11-09T03:00:02+00:00')
            self.assertIn('OAT',clock_snapshot(saved)['source'])
            self.assertTrue(Site.from_settings(load_settings()))
            with patch('astroall.timekeeping.boot_id',return_value='boot-B'):
                with self.assertRaises(ValueError): Site.from_settings(load_settings())

    def test_default_uninitialized_site_is_not_claimed_as_gps(self):
        sample={'UTC':'2026-11-09T03:00:00+00:00','LAT':'0','LON':'0','MONOTONIC':str(time.monotonic())}
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)):
            with self.assertRaisesRegex(ValueError,'LCD'): import_mount_time(sample)

    def test_visibility_boundaries_and_vector_agree_with_full_calculation(self):
        self.assertEqual([visibility_label(x) for x in (-.1,0,19.9,20)],['No visible ahora','Muy cercano al horizonte','Muy cercano al horizonte','Visible'])
        site=Site(17,-96);when=datetime(2026,11,9,3,tzinfo=timezone.utc)
        targets=[Target('a','A',10,20),Target('b','B',190,-20)]
        rows=atlas_visibility(targets,site,when)
        for target,row in zip(targets,rows):
            full=visibility(target,site,when)
            self.assertAlmostEqual(row['alt_deg'],full['alt_deg'],places=7)
            self.assertEqual(row['label'],full['visibility_label'])

    def test_recommendations_fit_extent_and_ff_never_claims_crop_lenses_cover_ff(self):
        target=Target('M31','Andrómeda',10.68,41.26,kind='G',major_arcmin=190,minor_arcmin=60)
        aps=recommend(target);ff=recommend(target,'Full Frame')
        for plan in (aps,ff):
            self.assertGreaterEqual(plan['field_w'],190/60*1.35)
            self.assertGreaterEqual(plan['field_h'],1.35)
            self.assertLessEqual(plan['exposure'],30)
            self.assertGreaterEqual(plan['count']*plan['exposure'],plan['minutes']*60)
        self.assertNotIn(ff['lens'],('18–45 mm','55–250 mm','TTArtisan 10 mm f/2'))
        self.assertGreaterEqual(ff['focal'],aps['focal'])
        self.assertTrue(any('estimado' in n for n in recommend(Target('x','X',0,0))['notes']))

    def test_plan_goto_precedes_capture_and_hidden_target_never_moves(self):
        target=Target('x','X',0,0);events=[]
        client=MagicMock();client.__enter__.return_value=client
        client.goto_eod.side_effect=lambda *args:events.append('goto')
        client.wait_slew.side_effect=lambda *args:events.append('arrived')
        def capture(*args):events.append('capture');return {'jpeg':'x.jpg'}
        with tempfile.TemporaryDirectory() as tmp,patch('astroall.session.load_settings',return_value={'latitude':17,'longitude':-96,'clock_confirmed':True}),patch('astroall.session.IndiClient',return_value=client),patch('astroall.session.visibility',return_value={'alt_deg':40,'ra_hours_eod':1,'dec_deg_eod':2}):
            result=execute([Block(1,1)],targets=[target],goto_first=True,capture=capture,state_file=Path(tmp)/'state.json')
            self.assertEqual(events,['goto','arrived','capture']);self.assertEqual(result['status'],'complete')
            events.clear()
            with patch('astroall.session.visibility',return_value={'alt_deg':-5}):
                with self.assertRaises(ValueError): execute([Block(1,1)],targets=[target],goto_first=True,capture=capture,state_file=Path(tmp)/'state.json')
            self.assertEqual(events,[])

    @unittest.skipUnless(os.name=='posix','Linux transport')
    def test_serial_open_does_not_pulse_dtr_and_disables_hangup(self):
        import termios
        handle=MagicMock();attrs=[0,0,termios.HUPCL,0,0,0,[]]
        with patch('serial.Serial',return_value=handle) as factory,patch('subprocess.run',return_value=MagicMock(returncode=1)),patch('fcntl.ioctl'),patch('termios.tcgetattr',return_value=attrs),patch('termios.tcsetattr') as tcset,patch('time.sleep'):
            from astroall.serial_transport import open_mount_serial
            open_mount_serial('/dev/ttyUSB0',19200)
            self.assertTrue(factory.call_args.kwargs['dsrdtr'])
            self.assertFalse(tcset.call_args.args[2][2]&termios.HUPCL)
            self.assertNotIn('dtr',handle.__dict__);self.assertNotIn('rts',handle.__dict__)

if __name__=='__main__':unittest.main()
