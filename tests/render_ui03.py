"""Capture our own Tk views under Xvfb; no desktop apps or devices are controlled."""
from pathlib import Path
import tkinter as tk
from PIL import ImageGrab
from astroall.dashboard import Dashboard

root=tk.Tk();app=Dashboard(root);root.geometry('1280x800');root.update()
destination=Path('/tmp/astroall-render03');destination.mkdir(exist_ok=True)
for page in ('session','atlas','mount','guide','focus'):
    app.show(page)
    if page=='atlas':
        from astroall.atlas_ui import search_targets
        app.atlas['query'].set('M31');search_targets(app)
    root.update();ImageGrab.grab().save(destination/(page+'.png'))
app.show('atlas');app.screen.enable=lambda:None;app.toggle_night();root.update();ImageGrab.grab().save(destination/'night.png')
if hasattr(app,'hand'): app.hand.close()
root.destroy()
print('Own application views rendered to',destination)
