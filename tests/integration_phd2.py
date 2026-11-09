"""Actual PHD2 binary, official simulator camera/scope and JSON-RPC client."""
import json
import os
from pathlib import Path
import subprocess
import time
from astroall.guiding import PHD2Client

def main():
    home=Path('/tmp/astroall-phd03-home');home.mkdir(exist_ok=True)
    (home/'.PHDGuidingV2').write_text('''ConfigVersion=2001
currentProfile=1
ServerMode=1
LoggingMode=0
[profile/1]
name=Astro One4All QA SIMULATION
FocalLength=200
[profile/1/camera]
LastMenuChoice=Simulator
pixelsize=3.75
AutoLoadDarks=0
AutoLoadDefectMap=0
[profile/1/scope]
LastMenuChoice=On-camera
CalibrationDuration=750
[profile/1/SimCam]
noise=0.2
pe_scale=0
dec_drift=0
dec_backlash=0
seeing_scale=0
''',encoding='utf-8')
    env=dict(os.environ,HOME=str(home),DISPLAY=':93',LC_ALL='C',XDG_CONFIG_HOME=str(home/'.config'),XDG_DATA_HOME=str(home/'.local/share'))
    xvfb=subprocess.Popen(['Xvfb',':93','-screen','0','1024x768x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    log=(home/'console.log').open('w');process=None;client=None
    try:
        time.sleep(1);process=subprocess.Popen(['/usr/local/bin/phd2'],env=env,stdout=log,stderr=log)
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            try: client=PHD2Client().__enter__();break
            except Exception: time.sleep(.5)
        if client is None: raise RuntimeError('PHD2 JSON-RPC did not start; inspect '+str(home/'console.log'))
        profiles=client.request('get_profiles');equipment=client.request('get_current_equipment')
        assert 'SIMULATION' in str(profiles),profiles
        client.request('set_connected',[True],timeout=15)
        assert client.request('get_connected')
        equipment=client.request('get_current_equipment')
        assert equipment.get('mount',{}).get('connected'),equipment
        client.request('set_exposure',[500]);client.request('loop')
        # Capture several actual simulator frames, then let PHD2 choose its star.
        until=time.monotonic()+4
        while time.monotonic()<until: client.read()
        star=client.request('find_star',timeout=15)
        settle=client.settle_parameters(pixels=3,seconds=1,timeout=60)
        calibrated=client.start_guiding(settle,recalibrate=True)
        client.assert_guiding();client.request('get_pixel_scale')
        dither=client.dither(1,settle=settle)
        until=time.monotonic()+3
        while time.monotonic()<until: client.read()
        snapshot=client.snapshot();client.request('stop_capture')
        print(json.dumps({'result':'passed','hardware':False,'backend':'PHD2 2.6.13 actual binary; official simulator camera and scope',
                          'profiles':profiles,'equipment':equipment,'star':star,'guide_settle':calibrated,'dither_settle':dither,
                          'samples':snapshot['samples'],'pixel_scale':snapshot['pixel_scale'],'rms_unit':snapshot['unit']},indent=2))
    finally:
        if client: client.__exit__()
        if process:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill();process.wait()
        xvfb.terminate();xvfb.wait(timeout=5);log.close()

if __name__=='__main__': main()
