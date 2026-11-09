"""Actual INDI/PHD2, simulated camera and serial OAT. No physical devices."""
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import threading
import time
from astroall.indi import IndiClient,IndiError
from astroall.oat_driver import DEVICE
from astroall.guide_profile import prepare
from astroall.guiding import PHD2Client
from astroall.mount_service import start_server,driver_devices


def main():
    master,slave=pty.openpty();port=os.ttyname(slave);os.close(slave)
    stop=threading.Event();commands=[]
    def firmware():
        pending=b''
        while not stop.is_set():
            try:
                if not select.select([master],[],[],.1)[0]: continue
                pending+=os.read(master,1024)
            except OSError: time.sleep(.05);continue
            while b'#' in pending:
                command,_,pending=pending.partition(b'#');command=command.decode()+'#';commands.append(command)
                reply={':GVP#':'OpenAstroTracker#',':GVN#':'v1.13.22#',':GR#':'05:00:00#',':GD#':"-00*30'00#",':GX#':'Idle,------,0,0,0,050000,-003000,,#'}.get(command,'')
                if reply: os.write(master,reply.encode())
    threading.Thread(target=firmware,daemon=True).start()
    home=Path.home();home.mkdir(exist_ok=True,parents=True)
    fifo=home/'.cache/astroall/indi.fifo';fifo.parent.mkdir(parents=True,exist_ok=True)
    if not fifo.exists(): os.mkfifo(fifo,0o600)
    log=(home/'integration.log').open('w');server=xvfb=phd=client=None
    try:
        server=subprocess.Popen(['indiserver','-p','7624','-f',str(fifo),'indi_simulator_ccd','indi_v4l2_ccd'],stdout=subprocess.DEVNULL,stderr=log)
        time.sleep(1);start_server('indi_astroall_oat')
        with IndiClient() as indi:
            assert driver_devices(indi,'indi_astroall_oat')==[DEVICE]
            indi.connect_mount(DEVICE,port,19200)
            assert float(indi.get(DEVICE,'EQUATORIAL_EOD_COORD')['values']['DEC'])==-.5
            camera=driver_devices(indi,'indi_v4l2_ccd')[0]
            indi.write(camera,'DEVICE_PORT',{'PORT':'/dev/video033-missing'},'Text')
            assert indi.get(camera,'DEVICE_PORT')['values']['PORT']=='/dev/video033-missing'
            try: indi.switch(camera,'CONNECTION','CONNECT')
            except IndiError: pass
            else: raise AssertionError('Missing V4L2 device was unexpectedly accepted')
            assert indi.get(camera,'CONNECTION')['values']['CONNECT']=='Off'
            indi.switch('CCD Simulator','CONNECTION','CONNECT')
        prepare('CCD Simulator',DEVICE,200,3.75,check_running=False,camera_id='test-only-simulator')
        xvfb=subprocess.Popen(['Xvfb',':94','-screen','0','1024x768x24','-nolisten','tcp'],stdout=log,stderr=log)
        time.sleep(1)
        phd=subprocess.Popen(['/usr/local/bin/phd2'],env=dict(os.environ,DISPLAY=':94',LC_ALL='C'),stdout=log,stderr=log)
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            try: client=PHD2Client().__enter__();break
            except OSError: time.sleep(.5)
        assert client,'PHD2 did not open API'
        client.request('set_connected',[True],timeout=40)
        equipment=client.request('get_current_equipment')
        assert equipment['camera']['connected'] and equipment['mount']['connected'],equipment
        assert 'INDI' in equipment['mount']['name'] and DEVICE in equipment['mount']['name'],equipment
        assert commands.count(':GVP#')==1 and commands.count(':GVN#')==1,commands
        try: prepare('CCD Simulator',DEVICE)
        except RuntimeError as exc: assert 'Cierra PHD2' in str(exc),exc
        else: raise AssertionError('PHD2 running profile protection failed')
        print(json.dumps({'result':'passed','physical_hardware':False,'backend':'Actual INDI 1.9.9 + PHD2 2.6.13; PTY OAT; CCD simulator',
                          'equipment':equipment,'real_firmware_dec_format':True,'guide_camera_port_written':True,
                          'no_camera_fallback':True,'mount_added_to_existing_server':True,'single_serial_owner':True},indent=2))
    finally:
        if client: client.__exit__()
        for process in (phd,xvfb,server):
            if process:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill();process.wait()
        stop.set();os.close(master);log.close()

if __name__=='__main__': main()
