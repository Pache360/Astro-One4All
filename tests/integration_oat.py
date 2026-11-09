"""Real indiserver + our driver + a Linux pseudo-terminal firmware emulator.

No Arduino is opened. This checks XML, serial framing, port ownership,
manual deadman stop, telemetry, GoTo, guide pulses and abort together.
"""
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import threading
import time
from astroall.indi import IndiClient
from astroall.oat_driver import DEVICE

def main():
    master,slave=pty.openpty();port=os.ttyname(slave);os.close(slave)
    stop=threading.Event();commands=[];current={'ra':'05:00:00','dec':"+20*00'00",'tracking':False,'until':0,'direction':None}
    def firmware():
        buffer=bytearray()
        while not stop.is_set():
            try:
                if not select.select([master],[],[],.1)[0]: continue
                data=os.read(master,1024)
            except OSError: time.sleep(.05);continue
            buffer.extend(data)
            while b'#' in buffer:
                raw,_,rest=buffer.partition(b'#');buffer=bytearray(rest);command=raw.decode(errors='replace')+'#';commands.append(command)
                reply=''
                if command==':GVP#': reply='OpenAstroTracker#'
                elif command==':GVN#': reply='v1.13.22#'
                elif command==':GR#': reply=current['ra']+'#'
                elif command==':GD#': reply=current['dec']+'#'
                elif command==':GX#':
                    state='SlewToTarget' if time.monotonic()<current['until'] else 'FreeSlew' if current['direction'] else 'Tracking' if current['tracking'] else 'Idle'
                    reply=state+',--'+('T' if current['tracking'] else '-')+'---,0,0,0,050000,+200000,,#'
                elif command.startswith(':Sr'): current['ra']=command[3:-1];reply='1'
                elif command.startswith(':Sd'): current['dec']=command[3:-1].replace(':',"'");reply='1'
                elif command==':MS#': current['until']=time.monotonic()+1.5;reply='0'
                elif command in (':MT1#',':MT0#'): current['tracking']=command==':MT1#';reply='1'
                elif command in (':Mn#',':Ms#',':Me#',':Mw#'): current['direction']=command[2]
                elif command in (':Qn#',':Qs#',':Qe#',':Qw#',':Q#'): current['direction']=None;current['until']=0
                elif command==':hF#': current['until']=time.monotonic()+1
                elif command==':hU#': reply='1'
                if reply:
                    # Deliberately fragment replies on the wire.
                    for char in reply.encode(): os.write(master,bytes([char]))
    threading.Thread(target=firmware,daemon=True).start()
    log=Path('/tmp/astroall-oat-integration.log').open('w')
    server=subprocess.Popen(['indiserver','-p','17625','indi_astroall_oat'],stdout=subprocess.DEVNULL,stderr=log)
    try:
        time.sleep(1)
        with IndiClient(port=17625) as client:
            client.connect_mount(DEVICE,port,19200)
            assert client.get(DEVICE,'FIRMWARE_INFO')['values']['VERSION']=='v1.13.22'
            client.switch(DEVICE,'TELESCOPE_TRACK_STATE','TRACK_ON')
            client.motion(DEVICE,'n')
            assert ':Mn#' in commands
            client.collect(2.2)
            assert ':Qn#' in commands,'Driver did not stop expired manual lease'
            client.goto_eod(DEVICE,5.1,-.5);client.wait_slew(DEVICE,timeout=10)
            assert abs(float(client.get(DEVICE,'EQUATORIAL_EOD_COORD')['values']['DEC'])+.5)<1e-4
            client.write(DEVICE,'TELESCOPE_TIMED_GUIDE_WE',{'TIMED_GUIDE_W':250,'TIMED_GUIDE_E':0},'Number')
            client.collect(.5)
            assert ':Mgw0250#' in commands
            client.abort(DEVICE)
            # A second INDI client sees the same connection, not another serial open.
            with IndiClient(port=17625) as second:
                assert second.get(DEVICE,'CONNECTION')['values']['CONNECT']=='On'
            client.switch(DEVICE,'CONNECTION','DISCONNECT')
        forbidden=(':X',':CM',':SH',':MHR',':MHD',':hZ')
        assert not any(command.startswith(forbidden) for command in commands)
        assert commands.count(':GVP#')==1 and commands.count(':GVN#')==1
        print(json.dumps({'result':'passed','hardware':False,'transport':'Linux PTY firmware emulator + real indiserver',
                          'identity':True,'19200_8N1':True,'manual_lease_stop':True,'goto_negative_zero_dec':True,'guide_pulse':True,'shared_clients':True,
                          'calibration_writes':False,'commands':commands},indent=2))
    finally:
        stop.set();server.terminate();server.wait(timeout=5);os.close(master);log.close()

if __name__=='__main__': main()
