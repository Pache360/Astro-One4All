"""Own UI visual QA with explicit simulated Oaxaca time/site, temporary HOME."""
import tempfile,time
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from PIL import ImageGrab
from astroall.dashboard import Dashboard
from astroall.timekeeping import import_mount_time
from astroall.atlas_ui import search_targets,to_plan

with tempfile.TemporaryDirectory() as temp,patch('pathlib.Path.home',return_value=Path(temp)):
    import_mount_time({'UTC':'2026-11-09T03:00:00+00:00','LAT':'17','LON':'-96','MONOTONIC':str(time.monotonic())})
    root=tk.Tk();app=Dashboard(root);root.geometry('1280x800');root.update()
    destination=Path('/tmp/astroall-render0310');destination.mkdir(exist_ok=True)
    def pump(seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:root.update();time.sleep(.02)
    app.show('atlas');app.atlas['kind'].set('Messier');search_targets(app);pump(10)
    app.atlas['tree'].selection_set('30');app.atlas['tree'].see('30');pump(3)
    for _ in range(100):
        if not app.atlas['sky_running']:break
        pump(.3)
    ImageGrab.grab().save(destination/'atlas.png')
    app.screen.enable=lambda:None;app.toggle_night();pump(1);ImageGrab.grab().save(destination/'night.png')
    app.screen.restore=lambda:None;app.toggle_night();to_plan(app);pump(1);ImageGrab.grab().save(destination/'session.png')
    app.show('system');pump(1);ImageGrab.grab().save(destination/'system.png')
    from astroall.preferences_ui import settings_window
    settings_window(app);pump(1);ImageGrab.grab().save(destination/'settings.png')
    for dialog in root.winfo_children():
        if isinstance(dialog,tk.Toplevel):dialog.destroy()
    from astroall.session_ui import clear_target
    clear_target(app);pump(1);ImageGrab.grab().save(destination/'current-field.png')
    if hasattr(app,'hand'):app.hand.close()
    root.destroy()
print('Own UI rendered with simulated site/time, without devices.')
