import base64
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from astroall.guide_camera import usb_difference,monochrome,device_identity
from astroall.guide_profile import prepare
from astroall.guide_preview import PreviewClient,save_image
from astroall.indi import IndiClient
from astroall.oat_driver import Driver
from tests.test_features03 import SerialFake

class ConnectionFixTests(unittest.TestCase):
    def test_rejected_manual_order_keeps_transport_and_telemetry(self):
        import queue,threading
        from astroall.mount_service import HandController
        from astroall.indi import IndiRejected
        controller=object.__new__(HandController)
        controller.commands=queue.Queue();controller.closing=threading.Event();controller.held='n';controller.device='OAT'
        errors=[];snapshots=[];controller.error=errors.append;controller.status=snapshots.append;controller.post=lambda f:f()
        class Client:
            def __init__(self): self.calls=[];self.polls=0;self.closed=0
            def motion(self,dev,direction=None,axis=None):
                self.calls.append((direction,axis))
                if direction: raise IndiRejected('Detén GoTo antes del movimiento manual.')
            def collect(self,*args):
                self.polls+=1
                if self.polls>=2: controller.closing.set()
            def snapshot(self,*args): return {'connected':True}
            def __exit__(self,*args): self.closed+=1
        client=Client();controller.client=client;controller.run()
        self.assertEqual(client.closed,1);self.assertTrue(snapshots)
        self.assertEqual(len(errors),1);self.assertIn('Orden no aplicada',errors[0])
        self.assertIn((None,'NS'),client.calls);self.assertIn((None,'WE'),client.calls)
    def test_unplug_identifies_usb_instead_of_internal(self):
        internal={'path':'internal','node':'video0','bus':'usb-4'}
        external={'path':'acteck','node':'video2','bus':'usb-1-2'}
        self.assertEqual(usb_difference([internal,external],[internal]),external)
        with self.assertRaises(RuntimeError): usb_difference([internal,external],[internal,external])
        with self.assertRaises(RuntimeError): usb_difference([internal,external],[])
    def test_webcam_is_monochrome_8bit_raw_before_phd2(self):
        class Client:
            properties={('cam','CCD_CAPTURE_FORMAT'):{'values':{'INDI_MONO':'Off','INDI_RGB':'On'}},
                        ('cam','CCD_STREAM_ENCODER'):{'values':{'RAW':'Off','MJPEG':'On'}}}
            def __init__(self): self.calls=[]
            def switch(self,*args): self.calls.append(args)
        client=Client();monochrome(client,'cam')
        self.assertEqual(client.calls,[('cam','CCD_CAPTURE_FORMAT','INDI_MONO'),('cam','CCD_STREAM_ENCODER','RAW')])
    def test_reconnect_existing_mount_does_not_reopen_or_change_port(self):
        class Client(IndiClient):
            def get(self,dev,name):
                values={'DRIVER_INFO':{'DRIVER_EXEC':'indi_astroall_oat'},'CONNECTION':{'CONNECT':'On'},
                        'DEVICE_PORT':{'PORT':'/dev/ttyUSB0'},'DEVICE_BAUD_RATE':{'BAUD_19200':'On'}}[name]
                return {'values':values}
            def write(self,*args): raise AssertionError('Connected mount must not be rewritten')
            def snapshot(self,*args): return {'connected':True}
        client=Client();client.properties[('OAT','DEVICE_PORT')]={}
        self.assertTrue(client.connect_mount('OAT','/dev/ttyUSB0',19200)['connected'])
        with self.assertRaisesRegex(RuntimeError,'otro puerto'): client.connect_mount('OAT','/dev/ttyUSB1',19200)
    def test_manual_axis_change_not_confused_with_goto(self):
        driver=Driver(io.StringIO(),lambda *_:SerialFake())
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)):
            driver.connect()
        driver.update('EQUATORIAL_EOD_COORD',state='Busy');driver.update('OAT_STATUS',{'STATE':'FreeSlew'})
        def move(): driver.process(ET.fromstring('<newSwitchVector device="Astro One4All OAT" name="TELESCOPE_MOTION_WE"><oneSwitch name="MOTION_WEST">On</oneSwitch></newSwitchVector>'))
        move();self.assertEqual(driver.properties['TELESCOPE_MOTION_WE']['state'],'Busy')
        driver.lease.clear();driver.target_deadline=1;move()
        self.assertEqual(driver.properties['TELESCOPE_MOTION_WE']['state'],'Alert')
    def test_preview_receives_only_one_camera_and_bounds_image(self):
        client=PreviewClient('USB');client.parser=ET.XMLPullParser(events=('start','end'));client.parser.feed('<stream>');client.depth=0;client.root=None
        blob=base64.b64encode(b'example-fits').decode()
        client.ingest(f'<setBLOBVector device="USB" name="CCD1"><oneBLOB name="CCD1" format=".fits">{blob}</oneBLOB></setBLOBVector>'.encode())
        self.assertEqual(client.image,b'example-fits')
        client.received=client.max_receive_bytes
        with self.assertRaises(RuntimeError): client.ingest(b'x')
    def test_raw_video_preview_requires_one_byte_per_pixel(self):
        client=PreviewClient('USB');client.parser=ET.XMLPullParser(events=('start','end'));client.parser.feed('<stream>');client.depth=0;client.root=None
        client.properties['USB','CCD_STREAM_FRAME']={'values':{'WIDTH':'2','HEIGHT':'2'}}
        blob=base64.b64encode(bytes([0,80,160,255])).decode()
        client.ingest(f'<setBLOBVector device="USB" name="CCD1"><oneBLOB name="CCD1" format=".stream">{blob}</oneBLOB></setBLOBVector>'.encode())
        self.assertEqual(client.shape,(2,2));self.assertEqual(len(client.image),4)
    def test_fixed_usb_device_is_identified_as_internal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);device=root/'video0';(device/'device').mkdir(parents=True)
            for name,value in (('idVendor','1bcf'),('idProduct','2c17'),('removable','fixed')): (device/name).write_text(value)
            self.assertEqual(device_identity('/dev/video0',root)['role'],'internal')
    def test_fits_preview_has_a_bounded_thumbnail(self):
        try:
            import numpy as np
            from astropy.io import fits
            from PIL import Image
        except ImportError: self.skipTest('Live dependencies')
        stream=io.BytesIO();fits.writeto(stream,np.arange(1280*720,dtype='uint16').reshape(720,1280))
        with tempfile.TemporaryDirectory() as tmp:
            result=save_image(stream.getvalue(),Path(tmp)/'preview.jpg')
            self.assertEqual((result['width'],result['height']),(1280,720))
            with Image.open(result['jpeg']) as image: self.assertLessEqual(image.width,640)
    def test_profile_clears_unsupported_ao_and_saves_focal_at_real_phd_key(self):
        import configparser
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'.PHDGuidingV2';prepare('USB','OAT',200,3.75,path,False,camera_id='usb')
            with path.open('a') as stream: stream.write('\n[profile/1/stepguider]\nLastMenuChoice=SX AO (INDI)\n')
            prepare('USB','OAT',250,3.75,path,False,camera_id='usb')
            config=configparser.RawConfigParser();config.optionxform=str;config.read_string('[root]\n'+path.read_text())
            self.assertFalse(config.has_option('profile/1/stepguider','LastMenuChoice'))
            self.assertEqual(config['profile/1/frame']['focalLength'],'250.0')

if __name__=='__main__': unittest.main()
