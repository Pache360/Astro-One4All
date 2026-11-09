import base64,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from astroall.indi import IndiClient
from astroall.guide_preview import capture_preview

class Connection039Tests(unittest.TestCase):
    def test_momentary_gps_read_ack_does_not_need_read_to_stay_on(self):
        class Client(IndiClient):
            def __init__(self):self.prop={'values':{'READ':'Off'},'state':'Idle','revision':0,'permission':'rw'};self.messages=[];self.sent=[]
            def get(self,*args):return self.prop
            def send(self,element):self.sent.append(element)
            def collect(self,*args):self.prop=dict(self.prop,revision=1,state='Ok')
        client=Client();result=client.switch('OAT','OAT_READ_SITE_TIME','READ')
        self.assertEqual(result['state'],'Ok');self.assertEqual(len(client.sent),1)

    def test_video_frame_is_confirmation_even_without_stream_on_echo(self):
        class Client:
            def __init__(self,*args):
                self.image=None;self.shape=None;self.messages=[];self.commands=[]
                self.properties={('cam','CONNECTION'):{'values':{'CONNECT':'On'}},('cam','DEVICE_PORT'):{'values':{'PORT':'/dev/video2'}},
                    ('cam','CCD_VIDEO_STREAM'):{'values':{'STREAM_ON':'Off','STREAM_OFF':'On'},'state':'Ok'},('cam','CCD_EXPOSURE'):{'state':'Idle'}}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def get(self,device,name):return self.properties[device,name]
            def snapshot(self,*args):return {}
            def send(self,element,text=None):self.commands.append(element)
            def collect(self,*args):self.image=bytes([0,80,160,255]);self.shape=(2,2)
        selected={'name':'Acteck','path':'/dev/video2','indi_device':'cam','role':'unknown'};client=Client()
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)),patch('astroall.guide_preview.profile',return_value=selected),patch('astroall.guide_preview.selected_device',return_value=selected),patch('astroall.guide_preview.PreviewClient',return_value=client),patch('astroall.guide_preview.diagnostic'):
            result=capture_preview();self.assertTrue(Path(result['jpeg']).exists())
            switches=[e for e in client.commands if e.tag=='newSwitchVector'];self.assertEqual(len(switches),2)
            self.assertEqual(switches[0].find("oneSwitch[@name='STREAM_ON']").text,'On')
            self.assertEqual(switches[1].find("oneSwitch[@name='STREAM_OFF']").text,'On')

    @unittest.skipUnless(os.name=='posix','Linux camera locking')
    def test_usb_init_error_includes_native_context_message_and_is_closed(self):
        import sys
        from astroall.camera import open_camera,CameraError
        from astroall.camera_diagnostic import CaptureReport
        gp=MagicMock();camera=gp.Camera.return_value
        context=gp.Context.return_value
        callbacks=[];context.set_error_func.side_effect=lambda f,*_:callbacks.append(f)
        def fail(ctx):callbacks[0](ctx,'PTP: connection refused by camera',None);raise RuntimeError('[-1] Unspecified error')
        camera.init.side_effect=fail
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)),patch.dict(sys.modules,{'gphoto2':gp}),patch('astroall.equipment.apply_camera_selection',return_value={'model':'Canon EOS R50','port':'usb:001,007'}):
            report=CaptureReport()
            with self.assertRaisesRegex(CameraError,'PTP: connection refused'):
                with open_camera(report):pass
            self.assertEqual(report.data['failed_stage'],'initializing_usb');self.assertIn('PTP:',report.data['driver_messages'][-1])
            camera.exit.assert_called_once_with(context);camera.capture.assert_not_called()
