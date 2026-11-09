import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from astroall.guide_camera import compatible_video,monochrome


class Geometry0311Tests(unittest.TestCase):
    def test_reapplies_mono_layout_after_hardware_format_change(self):
        class Client:
            properties={('USB','CCD_CAPTURE_FORMAT'):{'values':{'INDI_MONO':'On','INDI_RGB':'Off'}}}
            def __init__(self):self.calls=[]
            def switch(self,*args):self.calls.append(args)
        client=Client();monochrome(client,'USB',force=True)
        self.assertEqual(client.calls,[('USB','CCD_CAPTURE_FORMAT','INDI_MONO')])

    def test_reapplies_already_selected_size_after_kernel_format_renegotiation(self):
        class Client:
            def __init__(self):
                self.calls=[];self.synchronized=False
                self.properties={('USB','V4L2_FORMAT'):{'values':{'YUYV 4:2:2':'On'}},
                    ('USB','V4L2_SIZE_DISCRETE'):{'values':{'640x480':'On','1280x720':'Off'}},
                    ('USB','CCD_FRAME'):{'values':{'WIDTH':'1280','HEIGHT':'720'}}}
            def switch(self,*args):self.calls.append(args);self.synchronized=True
            def send(self,*args):pass
            def collect(self,*args):
                if self.synchronized:
                    for name in ('CCD_FRAME','CCD_STREAM_FRAME'):self.properties['USB',name]={'values':{'WIDTH':'640','HEIGHT':'480'}}
        client=Client();result=compatible_video(client,'USB')
        self.assertEqual(client.calls,[('USB','V4L2_SIZE_DISCRETE','640x480')]);self.assertEqual(result['confirmed_frames']['CCD_FRAME'],[640,480])

    def test_inconsistent_geometry_is_rejected_before_streaming(self):
        class Client:
            properties={('USB','V4L2_SIZE_DISCRETE'):{'values':{'640x480':'On'}},
                        ('USB','CCD_FRAME'):{'values':{'WIDTH':'1280','HEIGHT':'720'}}}
            def switch(self,*args):pass
            def send(self,*args):pass
            def collect(self,*args):pass
        with tempfile.TemporaryDirectory() as tmp,patch('pathlib.Path.home',return_value=Path(tmp)),patch('time.monotonic',side_effect=[0,4]):
            with self.assertRaisesRegex(RuntimeError,'no sincronizó'):compatible_video(Client(),'USB')
