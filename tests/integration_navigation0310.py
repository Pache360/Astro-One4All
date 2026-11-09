"""Regression: a real persistent OAT connection survives every Tk page rebuild."""
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import threading
import time
import tkinter as tk
from unittest.mock import patch
from astroall.dashboard import Dashboard
from astroall.indi import IndiClient
from astroall.oat_driver import DEVICE

def main(workflow=None):
    master,slave=pty.openpty();port=os.ttyname(slave);os.close(slave)
    stopping=threading.Event();commands=[];tracking={'enabled':True};manual=set()
    def firmware():
        buffer=b''
        while not stopping.is_set():
            try:
                if not select.select([master],[],[],.1)[0]: continue
                buffer+=os.read(master,4096)
            except OSError: time.sleep(.02);continue
            while b'#' in buffer:
                raw,_,buffer=buffer.partition(b'#');command=raw.decode()+'#';commands.append(command)
                reply={':GVP#':'OpenAstroTracker#',':GVN#':'v1.13.22#',':GR#':'05:00:00#',':GD#':"+20*00'00#"}.get(command,'')
                reply={':GC#':'11/08/26#',':GL#':'21:00:00#',':GG#':'+06#',':Gt#':'+17*00#',':Gg#':'+096*00#',':XGL#':'060000#',':XGH#':'030000#'}.get(command,reply)
                if command==':GX#': reply=('FreeSlew' if manual else 'Tracking' if tracking['enabled'] else 'Idle')+',--'+('T' if tracking['enabled'] else '-')+'---,0,0,0,050000,+200000,,#'
                if command in (':MT1#',':MT0#'): tracking['enabled']=command==':MT1#';reply='1'
                if command in (':Mn#',':Ms#',':Me#',':Mw#'): manual.add(command[2])
                if command in (':Qn#',':Qs#',':Qe#',':Qw#'): manual.discard(command[2])
                if command==':Q#': manual.clear()
                if reply: os.write(master,reply.encode())
    threading.Thread(target=firmware,daemon=True).start()
    log=Path('/tmp/astroall-navigation0310-indi.log').open('w')
    server=subprocess.Popen(['indiserver','-p','7624','indi_astroall_oat'],stdout=log,stderr=log)
    root=tk.Tk();app=Dashboard(root);root.geometry('1280x800');errors=[]
    dialogs=patch('astroall.dashboard.messagebox.showerror',side_effect=lambda title,text,**kw:errors.append(text));dialogs.start()
    root.report_callback_exception=lambda kind,value,tb:errors.append(str(value))
    def pump(seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline: root.update();time.sleep(.01)
    observations=[]
    try:
        pump(1);app.show('mount')
        app.hand.submit('connect',{'driver':'indi_astroall_oat','device':DEVICE,'port':port,'baud':'19200'})
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            pump(.1)
            if 'v1.13.22' in app.mount_status.get(): break
        assert 'v1.13.22' in app.mount_status.get(),app.log_lines
        hand=app.hand;socket_object=hand.client.sock
        workflow_result=workflow(app,root,pump) if workflow else None
        from astroall.atlas_ui import search_targets,to_plan
        from astroall.session_ui import clear_target
        app.show('atlas');app.atlas['query'].set('M31');search_targets(app);to_plan(app)
        assert app.plan_targets and clear_target(app)
        assert not app.plan_targets and not app.sequence['goto'].get() and not app.sequence['jpg_correct'].get()
        assert app.hand is hand and app.hand.client.sock is socket_object
        for cycle in range(3):
            app.hand.hold('n');pump(.5)
            for page in ('atlas','session','guide','focus','polar','system','mount'):
                app.show(page);pump(.8)
                connected=app.mount_snapshot.get(DEVICE+'/CONNECTION',{}).get('values',{}).get('CONNECT')=='On'
                observations.append({'cycle':cycle,'page':page,'connected':connected,'controller_same':app.hand is hand})
                assert connected and app.hand is hand and app.hand.client is not None,(page,app.log_lines)
                assert app.hand.client.sock is socket_object,'Navigation replaced the socket'
                assert not manual,'Navigation did not release manual movement'
                assert tracking['enabled'],'Navigation changed sidereal tracking'
        with IndiClient() as observer:
            assert observer.get(DEVICE,'CONNECTION')['values']['CONNECT']=='On'
        assert commands.count(':GVP#')==1 and commands.count(':GVN#')==1,commands
        assert not errors,errors
        result={'result':'passed','physical_hardware':False,'native_indi_driver':True,'transport':'Linux PTY OAT emulator',
                'page_changes':len(observations),'same_socket':True,'single_serial_open':True,'tracking_preserved':True,
                'manual_released_on_navigation':True,'target_cleared_without_reopening_mount':True,'observations':observations,'callback_errors':errors,'activity':app.log_lines,
                'integrated_workflow':workflow_result}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:
        if hasattr(app,'hand'): app.hand.close();pump(.5)
        root.destroy();server.terminate()
        try: server.wait(timeout=5)
        except subprocess.TimeoutExpired: server.kill();server.wait()
        stopping.set();os.close(master);log.close();dialogs.stop()

if __name__=='__main__': main()
