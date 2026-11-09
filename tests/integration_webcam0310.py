"""Full V4L2 -> INDI -> bounded FITS -> PHD2 mono video, virtual Linux webcam."""
import json
import os
from pathlib import Path
import pty
import select
import socket
import subprocess
import threading
import time
from unittest.mock import patch
from astroall.indi import IndiClient
from astroall.oat_driver import DEVICE
from astroall.guide_camera import video_devices,configure_camera
from astroall.guide_preview import capture_preview
from astroall.guide_profile import prepare
from astroall.guiding import PHD2Client

def main():
    devices=video_devices();selected=next(d for d in devices if d['node']=='/dev/video8')
    assert selected['path']=='/dev/v4l/by-id/usb-ALK-1054-200710_Integrated_Camera-video-index0',selected
    master,slave=pty.openpty();port=os.ttyname(slave);os.close(slave)
    stop=threading.Event();commands=[]
    def firmware():
        buffer=b''
        while not stop.is_set():
            try:
                if not select.select([master],[],[],.1)[0]: continue
                buffer+=os.read(master,1024)
            except OSError: time.sleep(.05);continue
            while b'#' in buffer:
                raw,_,buffer=buffer.partition(b'#');command=raw.decode()+'#';commands.append(command)
                reply={':GVP#':'OpenAstroTracker#',':GVN#':'v1.13.22#',':GR#':'05:00:00#',':GD#':"+20*00'00#",':GX#':'Tracking,--T---,0,0,0,050000,+200000,,#'}.get(command,'')
                reply={':GC#':'11/08/26#',':GL#':'21:00:00#',':GG#':'+06#',':Gt#':'+17*00#',':Gg#':'+096*00#',':XGL#':'060000#',':XGH#':'030000#'}.get(command,reply)
                if reply: os.write(master,reply.encode())
    threading.Thread(target=firmware,daemon=True).start()
    home=Path.home();home.mkdir(parents=True,exist_ok=True)
    log=(home/'webcam-test.log').open('w');server=phd=xvfb=client=None
    try:
        server=subprocess.Popen(['indiserver','-p','7624','indi_astroall_oat','indi_v4l2_ccd'],stdout=log,stderr=log)
        deadline=time.monotonic()+30
        while True:
            try:
                with socket.create_connection(('127.0.0.1',7624),timeout=1):pass
                break
            except OSError:
                if server.poll() is not None or time.monotonic()>=deadline:
                    raise RuntimeError('INDI did not become ready: '+(home/'webcam-test.log').read_text())
                time.sleep(.25)
        with IndiClient() as indi:
            ready=time.monotonic()+30
            while any(key not in indi.properties for key in ((DEVICE,'DRIVER_INFO'),('V4L2 CCD','DRIVER_INFO'))) and time.monotonic()<ready:
                indi.collect(.25)
            indi.connect_mount(DEVICE,port,19200)
            # A second Connect must reuse the same live serial owner.
            indi.connect_mount(DEVICE,port,19200)
            configure_camera(indi,'V4L2 CCD',selected)
            assert indi.get('V4L2 CCD','DEVICE_PORT')['values']['PORT']=='/dev/video8'
            assert indi.get('V4L2 CCD','CCD_CAPTURE_FORMAT')['values']['INDI_MONO']=='On'
        preview=capture_preview()
        assert Path(preview['jpeg']).stat().st_size<300000
        # Exercise the exact native INDI JPEG transport rejected in the user's log.
        from astroall.guide_camera import monochrome
        def jpeg_transport(client,device):
            monochrome(client,device);client.switch(device,'CCD_STREAM_ENCODER','MJPEG')
        with patch('astroall.guide_preview.monochrome',side_effect=jpeg_transport):
            jpeg_preview=capture_preview()
        assert jpeg_preview['source_format']=='.stream_jpg',jpeg_preview
        with IndiClient() as indi:monochrome(indi,'V4L2 CCD')
        prepare('V4L2 CCD',DEVICE,200,3.75,check_running=False,camera_id='virtual-webcam8')
        xvfb=subprocess.Popen(['Xvfb',':95','-screen','0','1024x768x24','-nolisten','tcp'],stdout=log,stderr=log)
        time.sleep(1)
        phd=subprocess.Popen(['/usr/local/bin/phd2'],env=dict(os.environ,DISPLAY=':95',LC_ALL='es_MX.UTF-8'),stdout=log,stderr=log)
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            try: client=PHD2Client().__enter__();break
            except OSError: time.sleep(.5)
        assert client,'PHD2 API unavailable'
        client.request('set_connected',[True],timeout=40)
        equipment=client.request('get_current_equipment')
        assert equipment['camera']['connected'] and equipment['mount']['connected'],equipment
        assert 'ao' not in equipment and 'aux_mount' not in equipment,equipment
        client.request('set_exposure',[500]);client.request('loop')
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            client.read()
            frames=[e for e in client.events if e.get('Event')=='LoopingExposures']
            if len(frames)>=3: break
        assert len(frames)>=3,'PHD2 did not receive at least three actual V4L2 frames'
        client.request('stop_capture')
        assert commands.count(':GVP#')==1 and commands.count(':GVN#')==1,commands
        print(json.dumps({'result':'passed','physical_hardware':False,'backend':'Linux vivid V4L2 capture + real INDI 1.9.9 + PHD2 2.6.13',
                          'devices':devices,'selected':selected,'preview':preview,'native_mjpeg_preview':jpeg_preview,'phd_equipment':equipment,
                          'phd_video_frames':len(frames),'locale':'es_MX.UTF-8','mount_reconnect_same_serial_owner':True},indent=2))
    finally:
        if client:
            try: client.request('stop_capture')
            except Exception: pass
            client.__exit__()
        for process in (phd,xvfb,server):
            if process:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill();process.wait()
        stop.set();os.close(master);log.close()

if __name__=='__main__': main()
