from datetime import datetime,timezone
import io
import json
import math
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from astroall.catalog import Catalog,Target,normalized
from astroall.geometry import parse_angle,correction_target,mosaic,offset
from astroall.solve import Position,separation_arcsec
from astroall.oat_protocol import OATProtocol,ProtocolError
from astroall.oat_driver import Driver,DEVICE
from astroall.guiding import PHD2Client,GuideError
from astroall.session import Block,execute
from astroall.sky import Site,eod_position,visibility,night_tracks

class CatalogTests(unittest.TestCase):
    def test_catalog_count_messier_and_spanish_search(self):
        c=Catalog();meta=c.metadata()
        self.assertEqual(len(c.search(messier_only=True,limit=500)),110)
        self.assertEqual(c.search('M 031')[0].messier,31)
        self.assertEqual(c.search('orion')[0].messier,42)
        self.assertTrue(c.search('Via Lactea'))
        self.assertTrue(c.search('M102')[0].name.endswith('(identificación tradicional)'))
        import sqlite3
        with c.connect() as connection:
            with self.assertRaises(sqlite3.OperationalError): connection.execute('DELETE FROM objects')
    def test_wraparound_region_includes_zero_ra(self):
        rows=Catalog().region(359.9,0,10,stars=True)
        self.assertTrue(any(r['ra_deg']<10 for r in rows))

class GeometryTests(unittest.TestCase):
    def test_negative_zero_and_ra_hours(self):
        self.assertEqual(parse_angle('-00:30:00'),-.5)
        self.assertEqual(parse_angle('12:00:00',True),180)
        with self.assertRaises(ValueError): parse_angle('24:00:00',True)
    def test_rotation_correction_across_ra_wrap_and_near_pole(self):
        for original,desired in [(Position(359.9,10),Position(.1,10)),(Position(25,89.5),Position(50,89.4))]:
            corrected=correction_target(original,original,desired)
            self.assertLess(separation_arcsec(corrected,desired),.01)
        with self.assertRaises(ValueError): correction_target(Position(1,0),Position(1,0),Position(10,0))
    def test_mosaic_serpentine_and_bounds(self):
        p=mosaic(Position(359,70),4,3,2,3,.2,45)
        self.assertEqual([(x['row'],x['column']) for x in p],[(1,1),(1,2),(1,3),(2,3),(2,2),(2,1)])
        self.assertTrue(all(0<=x['ra_deg']<360 for x in p))
        with self.assertRaises(ValueError): mosaic(Position(0,0),120,120,9,9)

class SerialFake:
    def __init__(self): self.commands=[];self.buffer=bytearray();self.closed=False;self.ms='0';self.track=True
    def write(self,data):
        command=data.decode();self.commands.append(command)
        response={':GVP#':'OpenAstroTracker#',':GVN#':'v1.13.22#',':GR#':'23:59:55#',':GD#':'-00*30:00#',':GX#':'Idle,--T,0,0,0,235955,-003000,#',':MS#':self.ms}
        response.update({':GC#':'11/08/26#',':GL#':'21:00:00#',':GG#':'+06#',':Gt#':'+17*00#',':Gg#':'+096*00#',':XGL#':'060000#',':XGH#':'030000#'})
        if command.startswith((':Sr',':Sd',':MT')): reply='1'
        else: reply=response.get(command,'')
        self.buffer.extend(reply.encode());return len(data)
    def flush(self): pass
    def read(self,size):
        data=bytes(self.buffer[:size]);del self.buffer[:size];return data
    def close(self): self.closed=True

class ProtocolTests(unittest.TestCase):
    def test_mixed_reply_framing_does_not_consume_next_command(self):
        serial=SerialFake();p=OATProtocol(serial)
        self.assertEqual(p.identify(),('OpenAstroTracker','v1.13.22'))
        p.tracking(True);p.rate(0);p.goto(.001,-.5);p.move('n');p.move('n',False);p.pulse('w',250)
        self.assertEqual(p.status()['dec'],-.5)
        self.assertIn(':Sd-00*30:00#',serial.commands);self.assertIn(':Mgw0250#',serial.commands)
        self.assertFalse(serial.buffer)
    def test_ms_one_is_rejected_not_interpreted_as_success(self):
        serial=SerialFake();serial.ms='1'
        with self.assertRaises(ProtocolError): OATProtocol(serial).goto(5,20)
        self.assertEqual(serial.commands.count(':MS#'),1)
    def test_incomplete_reply_faults_link_and_sends_single_stop(self):
        serial=SerialFake();p=OATProtocol(serial)
        with self.assertRaises(ProtocolError): p.command(':unknown#','hash',timeout=0)
        self.assertEqual(serial.commands,[':unknown#',':Q#'])
        with self.assertRaises(ProtocolError): p.tracking(True)
    def test_driver_manual_lease_and_no_calibration_commands(self):
        serial=SerialFake();d=Driver(io.StringIO(),lambda *_:serial)
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)):
            d.process(ET.fromstring(f'<newSwitchVector device="{DEVICE}" name="CONNECTION"><oneSwitch name="CONNECT">On</oneSwitch></newSwitchVector>'))
        d.process(ET.fromstring(f'<newSwitchVector device="{DEVICE}" name="TELESCOPE_MOTION_NS"><oneSwitch name="MOTION_NORTH">On</oneSwitch></newSwitchVector>'))
        self.assertIn(':Mn#',serial.commands);d.lease['n']=0;d.tick()
        self.assertIn(':Qn#',serial.commands);self.assertFalse(d.lease)
        self.assertFalse(any(x.startswith((':X','Main','MHR','MHD',':CM',':SH')) and x not in (':XGL#',':XGH#') for x in serial.commands))
        d.disconnect()

class GuidingTests(unittest.TestCase):
    def test_fragmented_events_and_real_settle_failure(self):
        c=PHD2Client();c.ingest(b'{"Event":"AppState","State":"Guiding"}\r\n{"Event":"GuideStep","RADistanceRaw":3,')
        c.ingest(b'"DECDistanceRaw":4}\r\n')
        self.assertEqual(c.snapshot()['total_rms'],5);self.assertEqual(c.snapshot()['unit'],'px')
        c.pixel_scale=2;self.assertEqual(c.snapshot()['total_rms'],10)
        c.ingest(b'{"Event":"SettleDone","Status":1,"Error":"lost star"}\n')
        with self.assertRaises(GuideError): c.wait_settle(10)

class PlanTests(unittest.TestCase):
    def test_failed_capture_is_uncertain_and_never_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'session.json';calls=[]
            def capture(*args): calls.append(args);raise RuntimeError('USB lost')
            with self.assertRaises(RuntimeError): execute([Block(2,2)],capture=capture,state_file=path)
            state=json.loads(path.read_text());self.assertTrue(state['uncertain_shot']);self.assertEqual(len(calls),1);self.assertEqual(state['status'],'error')
    def test_stop_during_bulb_does_not_count_partial_shot(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=execute([Block(2,60)],capture=lambda *_:{'interrupted':True},state_file=Path(tmp)/'state.json')
            self.assertEqual(result['completed'],0);self.assertEqual(result['status'],'stopped');self.assertFalse(result['uncertain_shot'])
    def test_plan_progress_and_calibration_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            events=[];result=execute([Block(2,2,delay=0)],capture=lambda *_:{'jpeg':'x.jpg','interrupted':False},emit=events.append,state_file=Path(tmp)/'state.json')
            self.assertEqual(result['status'],'complete');self.assertEqual([x['shot'] for x in events],[1,2])

class SkyTests(unittest.TestCase):
    def test_site_requires_real_coordinates_and_clock(self):
        with self.assertRaises(ValueError): Site.from_settings({'clock_confirmed':True})
        with self.assertRaises(ValueError): Site.from_settings({'latitude':17,'longitude':-96})
    def test_icrs_apparent_roundtrip_offline(self):
        try: import astropy
        except ImportError: self.skipTest('Astropy is provided by the Live image')
        site=Site(17,-96);when=datetime(2026,11,3,4,tzinfo=timezone.utc);p=Position(10,80)
        apparent=eod_position(p,site,when);back=eod_position(apparent,site,when,True)
        self.assertLess(separation_arcsec(p,back),.01)
        view=visibility(p,site,when);self.assertTrue(-90<=view['alt_deg']<=90)
        result=night_tracks([Catalog().get('NGC0224')],site,'2026-11-03',step_minutes=60)
        self.assertEqual(len(result['times_local']),25);self.assertEqual(len(result['tracks'][0]['altitudes']),25)

if __name__=='__main__': unittest.main()
