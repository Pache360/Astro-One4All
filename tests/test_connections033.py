import configparser
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from astroall.guide_camera import video_devices,selected_device,configure_camera
from astroall.guide_profile import prepare
from astroall.indi import IndiClient,IndiError
from astroall.mount_service import driver_devices
from astroall.oat_protocol import OATProtocol
from tests.test_features03 import SerialFake


class ConnectionsTests(unittest.TestCase):
    def test_shared_server_camera_blob_definition_is_not_an_image(self):
        import xml.etree.ElementTree as ET
        client=IndiClient();client.parser=ET.XMLPullParser(events=('start','end'))
        client.parser.feed('<stream>');client.depth=0;client.root=None
        client.ingest(b'<defBLOBVector device="V4L2 CCD" name="CCD1"><defBLOB name="CCD1"/></defBLOBVector>')
        self.assertFalse(client.properties)
        with self.assertRaises(IndiError):
            client.ingest(b'<setBLOBVector device="V4L2 CCD" name="CCD1"><oneBLOB name="CCD1">AAAA</oneBLOB></setBLOBVector>')

    def test_real_firmware_declination_apostrophe_and_negative_zero(self):
        class Serial(SerialFake):
            def write(self,data):
                result=super().write(data)
                if data==b':GD#': self.buffer=bytearray(b"-00*30'00#")
                return result
        serial=Serial();protocol=OATProtocol(serial)
        self.assertEqual(protocol.status()['dec'],-.5)
        self.assertEqual(protocol.transcript[1]['reply'],"-00*30'00#")

    def test_metadata_node_is_not_offered_and_names_are_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i in range(3): (root/f'video{i}').touch()
            def probe(path):
                number=Path(path).name[-1]
                return {'name':'Integrated' if number=='0' else 'Acteck WM20','bus':'usb-'+number,'capture':number!='2'}
            devices=video_devices(root,probe)
            self.assertEqual([d['name'] for d in devices],['Integrated','Acteck WM20'])
            self.assertIn('video1',devices[1]['label'])

    def test_missing_selected_usb_never_falls_back_to_integrated(self):
        integrated={'path':'/dev/video0','name':'Integrated','bus':'usb-internal'}
        with self.assertRaisesRegex(RuntimeError,'no se usará la integrada'):
            selected_device('/dev/v4l/by-id/acteck',[integrated])

    def test_same_number_reused_by_other_camera_is_rejected(self):
        with patch('astroall.guide_camera.profile',return_value={'path':'/dev/video1','name':'Acteck','bus':'usb-2'}):
            with self.assertRaisesRegex(RuntimeError,'otra cámara'):
                selected_device('/dev/video1',[{'path':'/dev/video1','name':'Integrated','bus':'usb-1'}])

    def test_camera_port_set_before_connect_not_video0(self):
        class Client:
            def __init__(self): self.port='/dev/video0';self.connected=False;self.calls=[];self.properties={}
            def get(self,device,name): return {'values':{'PORT':self.port} if name=='DEVICE_PORT' else {'CONNECT':'On' if self.connected else 'Off'}}
            def write(self,device,name,values,kind): self.calls.append((name,values));self.port=values['PORT']
            def switch(self,device,name,key): self.calls.append((name,key));self.connected=True
        client=Client();selection={'name':'Acteck','bus':'usb-2','path':'/dev/v4l/by-id/acteck','node':'/dev/video2'}
        with patch('astroall.guide_camera.save_profile') as save,patch('astroall.guide_camera.diagnostic'):
            configure_camera(client,'V4L2 CCD',selection)
            self.assertEqual(client.calls[0],('DEVICE_PORT',{'PORT':selection['node']}))
            self.assertEqual(client.calls[1],('CONNECTION','CONNECT'));save.assert_called_once()
        client.port='/dev/video0'
        with self.assertRaisesRegex(RuntimeError,'Desconecta'): configure_camera(client,'V4L2 CCD',selection)

    def test_mount_discovery_cannot_pick_a_camera_with_connection_property(self):
        class Client: properties={('V4L2 CCD','CONNECTION'):{},('V4L2 CCD','DRIVER_INFO'):{'values':{'DRIVER_EXEC':'indi_v4l2_ccd'}}}
        self.assertEqual(driver_devices(Client(),'indi_astroall_oat'),[])

    def test_phd_profile_preserves_existing_profiles_and_uses_indi_mount(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'.PHDGuidingV2'
            original='ConfigVersion=2001\ncurrentProfile=2\n[profile/2]\nname=prueba\n[profile/2/scope]\nLastMenuChoice=On-AO\n'
            path.write_text(original)
            prepare('V4L2 CCD','Astro One4All OAT',200,3.75,path,False)
            config=configparser.RawConfigParser();config.optionxform=str
            config.read_string('[root]\n'+path.read_text())
            self.assertEqual(config['profile/2/scope']['LastMenuChoice'],'On-AO')
            self.assertEqual(config['profile/3/scope']['LastMenuChoice'],'INDI Mount')
            self.assertEqual(config['profile/3/indi']['INDImount'],'Astro One4All OAT')
            self.assertEqual(config['profile/3/indi']['INDIcam'],'V4L2 CCD')
            self.assertEqual(config['profile/3/indi']['INDIcam_forcevideo'],'1')
            self.assertEqual(path.with_name(path.name+'.before-astroall033').read_text(),original)

    def test_changed_guide_camera_gets_a_fresh_phd_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'.PHDGuidingV2'
            prepare('V4L2 CCD','OAT',path=path,check_running=False,camera_id='usb-acteck')
            prepare('V4L2 CCD','OAT',path=path,check_running=False,camera_id='usb-other')
            config=configparser.RawConfigParser();config.optionxform=str
            config.read_string('[root]\n'+path.read_text())
            self.assertEqual(config['root']['currentProfile'],'2')
            self.assertEqual(config['profile/1']['AstroallCameraID'],'usb-acteck')
            self.assertEqual(config['profile/2']['AstroallCameraID'],'usb-other')

if __name__=='__main__': unittest.main()
