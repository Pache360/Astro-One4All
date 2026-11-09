"""Native offline WCS and simulated polar UI, without any physical devices."""
import hashlib,json,math,os,random,time
from pathlib import Path
import tkinter as tk
import numpy as np
from PIL import Image,ImageDraw,ImageGrab
from astroall.solve import solve_frame
from astroall.polar_camera import PolarSession,PolarSample,orientation,reticle
from astroall.polar import horizon_vector
from astroall.dashboard import Dashboard
from astroall.timekeeping import write_settings
from test_polar_images import base,rotation,wcs_from_basis


root=Path('/tmp/astroall-polar0313-proof');root.mkdir(exist_ok=True)
start=time.monotonic()
solved=solve_frame('/tmp/polar-qa-apod2.jpg',4.5,['/usr/share/astrometry'],root/'solver')
from astropy.wcs.utils import skycoord_to_pixel
sky=solved.sky(solved.width*.4,solved.height*.6)
x,y=skycoord_to_pixel(sky,solved.wcs(),origin=0,mode='all')
assert abs(x-solved.width*.4)<1e-5 and abs(y-solved.height*.6)<1e-5
native={'reference':'Official Astrometry.net apod2 demo (not redistributed)',
        'real_solve_field':True,'width':solved.width,'height':solved.height,
        'elapsed_seconds':time.monotonic()-start,'roundtrip_pixels':float(math.hypot(x-solved.width*.4,y-solved.height*.6))}

os.environ['HOME']=str(root/'home');Path.home().mkdir(exist_ok=True)
write_settings({'timezone':'America/Mexico_City','clock_confirmed':True,'latitude':17.,'longitude':-96.,'elevation':0})
session=PolarSession();axis=horizon_vector(.25,16.8);initial=base(axis,1)
for i in range(3):
    utc=f'2026-11-09T04:0{i}:00+00:00';physical=rotation(axis,20*i)@initial
    solution=wcs_from_basis(physical,utc);path=root/f'sky-{i}.jpg'
    image=Image.new('RGB',(solution.width,solution.height),'#080d1b');draw=ImageDraw.Draw(image);rng=random.Random(220+i)
    for _ in range(500):
        x,y=rng.randrange(solution.width),rng.randrange(solution.height);r=rng.choice((.4,.6,1,1.4));bright=rng.randint(50,210)
        draw.ellipse((x-r,y-r,x+r,y+r),fill=(bright,bright,min(255,bright+12)))
    overlay=reticle(solution,utc,17,-96,0)
    p=overlay['polaris']
    if p and p['inside']:
        x,y=p['x'],p['y'];draw.ellipse((x-3,y-3,x+3,y+3),fill='white')
    draw.text((16,16),'CIELO SIMULADO - SOLO DEMOSTRACION',fill='#d2c6ff');image.save(path)
    session.accept(PolarSample(solution,utc,str(path),'main:SIMULATION',orientation(solution,utc,17,-96).tolist(),60.),(17,-96,0))
assert 15<session.result['polar_error_arcmin']<25
window=tk.Tk();app=Dashboard(window);window.geometry('1366x768')
app.show('polar');app.polar['session']=session;app.polar['focal'].set('125');app.polar['ready'].set(True);app.show('polar')
for _ in range(12):window.update();time.sleep(.1)
ImageGrab.grab().save(root/'polar-day.png')
app.show('atlas');app.show('polar');assert app.polar['session'] is session
app.screen.enable=lambda:None;app.screen.restore=lambda:None;app.toggle_night()
for _ in range(5):window.update();time.sleep(.1)
ImageGrab.grab().save(root/'polar-night.png')
window.destroy()
result={'result':'passed','physical_hardware':False,'native_offline_solver':native,
        'synthetic_three_point_error_arcmin':session.result['polar_error_arcmin'],
        'reticle_and_night_ui_rendered':True,'measurements_survive_navigation':True,
        'mount_commands_sent':False,'source_sha256':{name:hashlib.sha256(Path('/opt/astroall-qa0313',name).read_bytes()).hexdigest() for name in ('astroall/solve.py','astroall/polar_camera.py','astroall/polar_ui.py')}}
(root/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
