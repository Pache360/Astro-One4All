import base64
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from astroall.guide_preview import PreviewClient,save_image
from astroall.guide_camera import compatible_video


class Video0310Tests(unittest.TestCase):
    def test_native_indi_mjpeg_blob_decodes_to_bounded_monochrome_preview(self):
        from PIL import Image
        buffer=io.BytesIO();Image.new('RGB',(1280,720),(120,60,30)).save(buffer,format='JPEG')
        client=PreviewClient('USB');client.parser=ET.XMLPullParser(events=('start','end'));client.parser.feed('<stream>');client.depth=0;client.root=None
        blob=base64.b64encode(buffer.getvalue()).decode()
        client.ingest(f'<setBLOBVector device="USB" name="CCD1"><oneBLOB name="CCD1" format=".stream_jpg">{blob}</oneBLOB></setBLOBVector>'.encode())
        self.assertEqual(client.image_format,'.stream_jpg')
        with tempfile.TemporaryDirectory() as tmp:
            result=save_image(client.image,Path(tmp)/'preview.jpg',jpeg=True)
            self.assertEqual((result['width'],result['height']),(1280,720))
            with Image.open(result['jpeg']) as image:self.assertEqual(image.mode,'L');self.assertLessEqual(image.width,640)

    def test_oversized_or_mislabeled_jpeg_is_rejected(self):
        from PIL import Image
        for size,format in [((2100,2100),'JPEG'),((20,20),'PNG')]:
            buffer=io.BytesIO();Image.new('L',size).save(buffer,format=format)
            with tempfile.TemporaryDirectory() as tmp,self.assertRaises(RuntimeError):save_image(buffer.getvalue(),Path(tmp)/'preview.jpg',jpeg=True)

    def test_uvc_mjpeg_prefers_yuyv_and_small_frame_before_streaming(self):
        class Client:
            def __init__(self):
                self.properties={('USB','V4L2_FORMAT'):{'values':{'Motion-JPEG':'On','YUYV 4:2:2':'Off'}},
                    ('USB','V4L2_SIZE_DISCRETE'):{'values':{'1280x720':'On','640x480':'Off'}}};self.calls=[]
            def switch(self,*args):self.calls.append(args)
            def send(self,*args):pass
            def collect(self,*args):self.properties['USB','CCD_FRAME']={'values':{'WIDTH':'640','HEIGHT':'480'}}
        client=Client();compatible_video(client,'USB')
        self.assertEqual(client.calls,[('USB','V4L2_FORMAT','YUYV 4:2:2'),('USB','V4L2_SIZE_DISCRETE','640x480')])
        client.calls.clear();client.properties['USB','CCD_VIDEO_STREAM']={'values':{'STREAM_ON':'On'}}
        with self.assertRaises(RuntimeError):compatible_video(client,'USB')
        self.assertEqual(client.calls,[])
