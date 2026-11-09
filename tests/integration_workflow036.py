"""One running UI: emulated OAT, real PHD2 guiding/dither and simulated Canon SD.

PHD2 uses its official star/guide-output simulator. The same emulated OAT is
connected as the PHD2 auxiliary telescope. No camera or telescope hardware used.
"""
import functools
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import tkinter as tk
from unittest.mock import patch
from PIL import Image,ImageDraw
from astroall.guiding import PHD2Client
from astroall.oat_driver import DEVICE
from astroall.session import execute
from astroall import session_ui
from astroall.guide_ui import status as guide_status
from integration_navigation036 import main


def workflow(app,root,pump):
    home=Path.home();card=home/'simulated-canon-sd';card.mkdir(exist_ok=True)
    (home/'.local/state/astroall/ui-errors.jsonl').unlink(missing_ok=True)
    config=home/'.PHDGuidingV2'
    config.write_text('''ConfigVersion=2001
currentProfile=1
ServerMode=1
LoggingMode=1
[profile/1]
name=Astro One4All WORKFLOW SIMULATION ONLY
[profile/1/frame]
focalLength=200
[profile/1/camera]
LastMenuChoice=Simulator
pixelsize=3.75
AutoLoadDarks=0
AutoLoadDefectMap=0
[profile/1/scope]
LastMenuChoice=On-camera
LastAuxMenuChoice=INDI Mount
CalibrationDuration=750
[profile/1/indi]
INDIhost=localhost
INDIport=7624
INDImount=Astro One4All OAT
[profile/1/SimCam]
noise=0.2
pe_scale=0
dec_drift=0
dec_backlash=0
seeing_scale=0
[profile/1/guider]
StarMinHFD=1.0
''',encoding='utf-8')
    console=(home/'workflow-phd2.log').open('w')
    phd=subprocess.Popen(['/usr/local/bin/phd2'],env=dict(os.environ,LC_ALL='C'),stdout=console,stderr=console)
    client=None;result={};navigation=[];snapshots=[];capture_calls=[]
    def wait_for(condition,seconds):
        deadline=time.monotonic()+seconds
        while not condition() and time.monotonic()<deadline: pump(.1)
        assert condition(),app.log_lines
    def check_connected(page):
        connected=app.mount_snapshot.get(DEVICE+'/CONNECTION',{}).get('values',{}).get('CONNECT')=='On'
        assert connected and app.hand.client is not None,(page,app.log_lines)
        assert app.mount_badge.get()=='Montura: conectada'
        navigation.append({'page':page,'capture_busy':app.busy,'mount_connected':connected})
    try:
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            try: client=PHD2Client().__enter__();break
            except OSError: pump(.3)
        assert client,'PHD2 did not start'
        client.request('set_connected',[True],timeout=65)
        equipment=client.request('get_current_equipment')
        assert equipment['camera']['connected'] and equipment['mount']['connected'],equipment
        assert equipment.get('aux_mount',{}).get('connected'),equipment
        assert DEVICE in equipment['aux_mount']['name'],equipment
        client.request('set_exposure',[500]);client.request('loop');pump(4)
        client.request('find_star',timeout=15)
        app.show('guide')
        def progress(value):
            snapshots.append(value)
            app.post(lambda v=value:guide_status(app,v))
        def calibrate():
            with PHD2Client() as phd_client:
                phd_client.request('get_pixel_scale')
                phd_client.start_guiding(phd_client.settle_parameters(3,1,90),recalibrate=True,progress=progress)
            return 'Calibración y guiado simulados confirmados.'
        app.task('Calibrando PHD2 simulado…',calibrate)
        deadline=time.monotonic()+110
        pages=('atlas','session','mount','guide','focus','polar','system')
        index=0
        while app.busy and time.monotonic()<deadline:
            app.show(pages[index%len(pages)]);pump(.35);check_connected(app.current_page);index+=1
        assert not app.busy and not app.last_task_error,app.log_lines
        client.assert_guiding();result['calibration_guiding_confirmed']=True
        assert snapshots and any(v['state']=='Guiding' for v in snapshots),snapshots[-2:]

        def capture(cache,exposure,iso,stop):
            number=len(capture_calls)+1;capture_calls.append(number)
            if stop.wait(.7): return {'interrupted':True}
            cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
            raw=card/f'SIM_{number:04d}.CR3';jpeg=card/f'SIM_{number:04d}.JPG'
            raw.write_bytes(b'SIMULATED CANON RAW PLACEHOLDER - NOT A REAL CR3')
            image=Image.new('RGB',(640,360),(4,6,12));draw=ImageDraw.Draw(image)
            for i in range(30):
                x=(i*83+number*3)%640;y=(i*47)%360;draw.ellipse((x,y,x+2,y+2),fill=(200,200,200))
            image.save(jpeg,'JPEG');destination=cache/jpeg.name;shutil.copy2(jpeg,destination)
            return {'jpeg':str(destination),'sd_raw':raw.name,'sd_jpeg':jpeg.name,'downloaded_bytes':destination.stat().st_size,
                    'exposure_seconds':exposure,'interrupted':False,'bulb':False,'simulation':True}
        app.show('session');s=app.sequence
        s['count'].set('6');s['exposure'].set('1');s['delay'].set('0.1');s['guide'].set(True);s['dither'].set('2')
        with patch.object(session_ui,'execute',functools.partial(execute,capture=capture)),patch.object(session_ui.messagebox,'askyesno',return_value=True):
            session_ui.start(app)
        assert app.busy
        # Deliberately deliver one late callback from a removed view: this used
        # to stop Dashboard.poll and therefore all visible equipment updates.
        stale=tk.Label(app.content,text='expired test view');stale.destroy()
        app.post(lambda:stale.configure(text='late result'))
        deadline=time.monotonic()+130;index=0
        while app.busy and time.monotonic()<deadline:
            app.show(pages[index%len(pages)]);pump(.4);check_connected(app.current_page);index+=1
            if index==5:
                with patch.object(app.screen,'enable'),patch.object(app.screen,'restore'):
                    app.toggle_night();app.toggle_night()
        assert not app.busy and not app.last_task_error,app.log_lines
        assert app.completed==6 and len(capture_calls)==6,(app.completed,capture_calls)
        assert len(list(card.glob('*.CR3')))==6 and len(list(card.glob('*.JPG')))==6
        assert not list((home/'.cache/astroall/jpg').glob('*.CR3'))
        state=json.loads((home/'.local/state/astroall/session.json').read_text())
        assert state['status']=='complete' and state['completed']==6,state
        client.assert_guiding();client.read()
        # Session used its own real PHD2 client. Its dither requests must have
        # generated settle events visible to this independent observer.
        assert sum(e.get('Event')=='SettleDone' and e.get('Status')==0 for e in client.events)>=2,list(client.events)[-10:]
        ui_log=home/'.local/state/astroall/ui-errors.jsonl'
        ui_errors=[json.loads(line) for line in ui_log.read_text().splitlines()]
        assert len(ui_errors)==1 and 'invalid command name' in ui_errors[0]['error'],ui_errors
        result.update(result='passed',physical_hardware=False,main_camera='explicit simulated Canon card + JPEG capture fixture',
                      phd2='real binary, official star/guide-output simulator, INDI OAT auxiliary telescope',
                      equipment=equipment,captures_complete=6,raw_in_simulated_camera_card_only=True,
                      real_dither_settle_events=True,injected_expired_callback_recovered=True,
                      navigation_during_calibration_and_capture=navigation,
                      same_indi_serial_owner=True,guide_samples=len(snapshots))
        client.request('stop_capture')
        return result
    finally:
        if client:
            try: client.request('stop_capture')
            except Exception: pass
            client.__exit__()
        phd.terminate()
        try: phd.wait(timeout=5)
        except subprocess.TimeoutExpired: phd.kill();phd.wait()
        console.close()

if __name__=='__main__': main(workflow)
