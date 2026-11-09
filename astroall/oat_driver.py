"""Small native INDI OAT driver. Serial commands run only in this process.

Run under indiserver through indi_astroall_oat. Does not expose calibration,
sync, set-home, Hall homing or firmware-upload commands.
"""
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import queue
import sys
import threading
import time
import traceback
import xml.etree.ElementTree as ET
from .oat_protocol import OATProtocol

DEVICE='Astro One4All OAT'

class Driver:
    def __init__(self,output=None,opener=None):
        self.output=output or sys.stdout;self.opener=opener or self.open_serial
        self.serial=None;self.protocol=None;self.properties={};self.lease={};self.pulses={}
        self.next_poll=0;self.poll_time=0;self.target_deadline=None
        self.define('CONNECTION','Switch',{'CONNECT':'Off','DISCONNECT':'On'},rule='OneOfMany')
        self.define('DEVICE_PORT','Text',{'PORT':'/dev/ttyACM0'})
        self.define('DEVICE_BAUD_RATE','Switch',{f'BAUD_{x}':'On' if x==19200 else 'Off' for x in (9600,19200,38400,57600,115200)},rule='OneOfMany')
        self.define('DRIVER_INFO','Text',{'DRIVER_NAME':'Astro One4All OAT','DRIVER_EXEC':'indi_astroall_oat','DRIVER_VERSION':'0.3','DRIVER_INTERFACE':'5'},permission='ro')
        self.define('FIRMWARE_INFO','Text',{'PRODUCT':'Sin consultar','VERSION':'Sin consultar','UTC':''},permission='ro')
        self.define('OAT_SITE_TIME','Text',{k:'' for k in ('UTC','LAT','LON','MONOTONIC','LST_HOURS','OAT_HA_HOURS','SOURCE')},permission='ro')
        self.define('OAT_READ_SITE_TIME','Switch',{'READ':'Off'},rule='AtMostOne')
        self.define('OAT_STATUS','Text',{'STATE':'Disconnected','RAW':'','POSITION_SOURCE':'Calculated motor steps; no encoders'},permission='ro')
        self.define('EQUATORIAL_EOD_COORD','Number',{'RA':0,'DEC':0},bounds={'RA':(0,24,0),'DEC':(-90,90,0)})
        self.define('ON_COORD_SET','Switch',{'TRACK':'On'},rule='OneOfMany')
        self.define('TELESCOPE_TRACK_STATE','Switch',{'TRACK_ON':'Off','TRACK_OFF':'On'},rule='OneOfMany')
        # Rate changes never rewrite the firmware's speed calibration.
        self.define('TELESCOPE_SLEW_RATE','Switch',{'SLEW_GUIDE':'On','SLEW_CENTERING':'Off','SLEW_FIND':'Off','SLEW_MAX':'Off'},rule='OneOfMany')
        self.define('TELESCOPE_MOTION_NS','Switch',{'MOTION_NORTH':'Off','MOTION_SOUTH':'Off'},rule='AtMostOne')
        self.define('TELESCOPE_MOTION_WE','Switch',{'MOTION_WEST':'Off','MOTION_EAST':'Off'},rule='AtMostOne')
        self.define('TELESCOPE_ABORT_MOTION','Switch',{'ABORT':'Off'},rule='AtMostOne')
        self.define('TELESCOPE_TIMED_GUIDE_NS','Number',{'TIMED_GUIDE_N':0,'TIMED_GUIDE_S':0},bounds={k:(0,9999,1) for k in ('TIMED_GUIDE_N','TIMED_GUIDE_S')})
        self.define('TELESCOPE_TIMED_GUIDE_WE','Number',{'TIMED_GUIDE_W':0,'TIMED_GUIDE_E':0},bounds={k:(0,9999,1) for k in ('TIMED_GUIDE_W','TIMED_GUIDE_E')})
        self.define('TELESCOPE_PARK','Switch',{'PARK':'Off','UNPARK':'On'},rule='OneOfMany')
        self.define('OAT_EXISTING_HOME','Switch',{'GO':'Off'},rule='AtMostOne')

    def open_serial(self,port,baud):
        from .serial_transport import open_mount_serial
        return open_mount_serial(port,baud)

    def emit(self,element):
        self.output.write(ET.tostring(element,encoding='unicode')+'\n');self.output.flush()

    def define(self,name,kind,values,permission='rw',rule=None,bounds=None):
        self.properties[name]={'kind':kind,'values':dict(values),'perm':permission,'rule':rule,'bounds':bounds or {},'state':'Idle'}

    def publish(self,name,definition=False):
        prop=self.properties[name];kind=prop['kind']
        attrs={'device':DEVICE,'name':name,'state':prop['state'],'timeout':'10'}
        if definition:
            attrs.update(label=name,group='Mount',perm=prop['perm'])
            if kind=='Switch': attrs['rule']=prop['rule'] or 'AnyOfMany'
        root=ET.Element(('def' if definition else 'set')+kind+'Vector',attrs)
        for key,value in prop['values'].items():
            child_attrs={'name':key}
            if definition:
                child_attrs['label']=key
                if kind=='Number':
                    lo,hi,step=prop['bounds'].get(key,(-1e9,1e9,0))
                    child_attrs.update(format='%10.6m' if key in ('RA','DEC') else '%g',min=str(lo),max=str(hi),step=str(step))
            ET.SubElement(root,('def' if definition else 'one')+kind,child_attrs).text=str(value)
        self.emit(root)

    def update(self,name,values=None,state='Ok'):
        prop=self.properties[name]
        if values is not None: prop['values'].update(values)
        prop['state']=state;self.publish(name)

    def message(self,text): self.emit(ET.Element('message',{'device':DEVICE,'message':str(text)[:500]}))

    def diagnostic(self,stage,error=None):
        try:
            path=Path.home()/'.local/state/astroall/mount-diagnostic.json';path.parent.mkdir(parents=True,exist_ok=True)
            value={'stage':stage,'utc':datetime.now(timezone.utc).isoformat(),
                   'port':self.properties['DEVICE_PORT']['values']['PORT'],
                   'transcript':list(self.protocol.transcript) if self.protocol else [],
                   'firmware':self.properties['FIRMWARE_INFO']['values']}
            if error: value.update(error=str(error),traceback=traceback.format_exc())
            temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(path)
        except OSError: pass

    def disconnect(self):
        if self.protocol:
            # Directional stop preserves sidereal tracking. Disconnect never parks.
            for direction in list(self.lease):
                try: self.protocol.move(direction,False)
                except Exception: pass
        if self.serial: self.serial.close()
        self.serial=self.protocol=None;self.lease.clear();self.pulses.clear();self.target_deadline=None
        self.update('CONNECTION',{'CONNECT':'Off','DISCONNECT':'On'})

    def connect(self):
        port=self.properties['DEVICE_PORT']['values']['PORT']
        if not port.startswith('/dev/') or len(port)>256: raise ValueError('Puerto Linux inválido.')
        baud=int(next(k.removeprefix('BAUD_') for k,v in self.properties['DEVICE_BAUD_RATE']['values'].items() if v=='On'))
        try:
            self.serial=self.opener(port,baud);self.protocol=OATProtocol(self.serial)
            product,version=self.protocol.identify();utc=datetime.now(timezone.utc).isoformat()
            self.update('FIRMWARE_INFO',{'PRODUCT':product,'VERSION':version,'UTC':utc})
            record={'utc':utc,'port':port,'baud':baud,'framing':'8N1',':GVP#':product+'#',':GVN#':version+'#'}
            path=Path.home()/'.local/state/astroall/oat-identity.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists() and path.stat().st_size>131072: path.replace(path.with_suffix('.previous.jsonl'))
            with path.open('a',encoding='utf-8') as stream: stream.write(json.dumps(record)+'\n')
            self.protocol.require_supported(product,version)
            self.poll_status();self.update('CONNECTION',{'CONNECT':'On','DISCONNECT':'Off'});self.diagnostic('connected')
            self.read_site_time()
        except Exception as exc:
            self.diagnostic('connection_error',exc);self.disconnect();raise

    def poll_status(self):
        status=self.protocol.status();self.poll_time=time.monotonic();self.next_poll=self.poll_time+1
        self.update('EQUATORIAL_EOD_COORD',{'RA':status['ra'],'DEC':status['dec']},'Busy' if status['slewing'] else 'Ok')
        self.update('TELESCOPE_TRACK_STATE',{'TRACK_ON':'On' if status['tracking'] else 'Off','TRACK_OFF':'Off' if status['tracking'] else 'On'})
        self.update('TELESCOPE_PARK',{'PARK':'On' if status['parked'] else 'Off','UNPARK':'Off' if status['parked'] else 'On'},'Busy' if status['state']=='Parking' else 'Ok')
        self.update('OAT_STATUS',{'STATE':status['state'],'RAW':status['raw']})
        if not status['slewing']: self.target_deadline=None

    def read_site_time(self):
        from .mount_time import read_site_time
        try:
            self.update('OAT_SITE_TIME',read_site_time(self.protocol))
            self.update('OAT_READ_SITE_TIME',{'READ':'Off'})
        except Exception as exc:
            self.update('OAT_SITE_TIME',state='Alert');self.update('OAT_READ_SITE_TIME',{'READ':'Off'},'Alert')
            self.message('Hora/ubicación OAT no importadas: '+str(exc))
            if self.protocol.failed: raise

    def process(self,element):
        if element.tag=='getProperties':
            if element.get('device') not in (None,'',DEVICE): return
            for name in self.properties:
                if element.get('name') in (None,'',name): self.publish(name,True)
            return
        if element.get('device')!=DEVICE or not element.tag.startswith('new'): return
        name=element.get('name');prop=self.properties.get(name)
        if prop is None or prop['perm']=='ro': return
        try:
            if element.tag!='new'+prop['kind']+'Vector': raise ValueError('Tipo de propiedad inválido.')
            values={child.get('name'):(child.text or '').strip() for child in element}
            if not values or not set(values)<=set(prop['values']): raise ValueError('Miembro INDI no reconocido.')
            if prop['kind']=='Switch':
                if any(x not in ('On','Off') for x in values.values()): raise ValueError('Switch inválido.')
                selected=[k for k,v in values.items() if v=='On']
                if len(selected)>1: raise ValueError('Solo una dirección o estado a la vez.')
            if name=='CONNECTION':
                if values.get('CONNECT')=='On' and not self.protocol: self.connect()
                elif values.get('DISCONNECT')=='On': self.disconnect()
                else: self.publish(name)
                return
            if name in ('DEVICE_PORT','DEVICE_BAUD_RATE'):
                if self.protocol: raise ValueError('Desconecta antes de cambiar puerto o baudios.')
                if name=='DEVICE_BAUD_RATE' and len(selected)!=1: raise ValueError('Elige una velocidad.')
                self.update(name,{k:('On' if k in selected else 'Off') for k in prop['values']} if name=='DEVICE_BAUD_RATE' else values)
                return
            if not self.protocol: raise RuntimeError('Conecta primero el OAT.')
            if name=='OAT_READ_SITE_TIME':
                if self.lease or self.pulses or self.target_deadline: raise RuntimeError('Lee la hora/ubicación entre movimientos y pulsos de guiado.')
                self.read_site_time();return
            if name=='ON_COORD_SET':
                if values.get('TRACK')!='On': raise ValueError('Solo GoTo con seguimiento; Sync no está expuesto.')
                self.update(name,{'TRACK':'On'});return
            if name=='EQUATORIAL_EOD_COORD':
                if set(values)!={'RA','DEC'}: raise ValueError('Se necesitan ambas coordenadas.')
                if self.lease or self.pulses: raise RuntimeError('Detén el mando y el guiado antes de GoTo.')
                self.protocol.goto(float(values['RA']),float(values['DEC']));self.target_deadline=time.monotonic()+300
                self.update(name,state='Busy')
            elif name=='TELESCOPE_TRACK_STATE':
                if len(selected)!=1: raise ValueError('Elige seguimiento activo o parado.')
                self.protocol.tracking(selected[0]=='TRACK_ON');self.update(name,{k:'On' if k in selected else 'Off' for k in prop['values']})
            elif name=='TELESCOPE_SLEW_RATE':
                if len(selected)!=1: raise ValueError('Elige una velocidad.')
                self.protocol.rate(list(prop['values']).index(selected[0]));self.update(name,{k:'On' if k in selected else 'Off' for k in prop['values']})
            elif name in ('TELESCOPE_MOTION_NS','TELESCOPE_MOTION_WE'):
                directions={'MOTION_NORTH':'n','MOTION_SOUTH':'s','MOTION_WEST':'w','MOTION_EAST':'e'}
                for key in prop['values']:
                    direction=directions[key]
                    if key not in selected and direction in self.lease: self.protocol.move(direction,False);self.lease.pop(direction)
                if selected:
                    if self.target_deadline or self.properties['OAT_STATUS']['values']['STATE'] in ('SlewToTarget','Parking','Homing'):
                        raise RuntimeError('Detén GoTo antes del movimiento manual.')
                    direction=directions[selected[0]]
                    if direction not in self.lease: self.protocol.move(direction)
                    self.lease[direction]=time.monotonic()+1.5
                self.update(name,{k:'On' if k in selected else 'Off' for k in prop['values']},'Busy' if selected else 'Ok')
            elif name.startswith('TELESCOPE_TIMED_GUIDE_'):
                numbers={k:float(v) for k,v in values.items()}
                if any(not math.isfinite(v) or not 0<=v<=9999 for v in numbers.values()): raise ValueError('Pulso fuera de rango.')
                active=[(k,int(v)) for k,v in numbers.items() if int(v)>0]
                if len(active)>1 or self.lease or self.properties['EQUATORIAL_EOD_COORD']['state']=='Busy': raise ValueError('Pulso incompatible con el movimiento actual.')
                if active:
                    key,duration=active[0];self.protocol.pulse(key[-1].lower(),duration);self.pulses[name]=time.monotonic()+duration/1000
                    self.update(name,{k:duration if k==key else 0 for k in prop['values']},'Busy')
                else: self.update(name,{k:0 for k in prop['values']})
            elif name=='TELESCOPE_ABORT_MOTION':
                self.protocol.abort();self.lease.clear();self.pulses.clear();self.target_deadline=None
                for key in ('TELESCOPE_MOTION_NS','TELESCOPE_MOTION_WE'): self.update(key,{k:'Off' for k in self.properties[key]['values']})
                self.update(name,{'ABORT':'Off'})
            elif name=='OAT_EXISTING_HOME' and values.get('GO')=='On':
                if self.lease or self.pulses: raise RuntimeError('Suelta el mando y detén el guiado antes de volver a Home.')
                self.protocol.home();self.target_deadline=time.monotonic()+300;self.update(name,{'GO':'Off'})
            elif name=='TELESCOPE_PARK':
                if len(selected)!=1: raise ValueError('Elige Park o Unpark.')
                if self.lease or self.pulses: raise RuntimeError('Suelta el mando y detén el guiado antes de Park.')
                if selected[0]=='PARK': self.protocol.park();self.target_deadline=time.monotonic()+300
                else: self.protocol.unpark()
                self.update(name,state='Busy' if selected[0]=='PARK' else 'Ok')
            else: raise ValueError('Operación no disponible.')
        except Exception as exc:
            self.message(exc);self.update(name,state='Alert')
            if self.protocol and self.protocol.failed: self.disconnect();self.update('CONNECTION',state='Alert')

    def tick(self):
        if not self.protocol: return
        try:
            now=time.monotonic()
            for direction,deadline in list(self.lease.items()):
                if now>=deadline:
                    self.protocol.move(direction,False);del self.lease[direction]
                    name='TELESCOPE_MOTION_NS' if direction in 'ns' else 'TELESCOPE_MOTION_WE'
                    self.update(name,{k:'Off' for k in self.properties[name]['values']})
            for name,deadline in list(self.pulses.items()):
                if now>=deadline:
                    del self.pulses[name];self.update(name,{k:0 for k in self.properties[name]['values']})
            if self.target_deadline and now>self.target_deadline:
                self.protocol.abort();self.target_deadline=None;self.update('EQUATORIAL_EOD_COORD',state='Alert');self.message('Movimiento detenido al superar 300 s.')
            if now>=self.next_poll: self.poll_status()
        except Exception as exc:
            self.diagnostic('poll_error',exc)
            self.message(exc)
            try: self.protocol.abort()
            except Exception: pass
            self.disconnect();self.update('CONNECTION',state='Alert')

def main():
    inbox=queue.Queue(maxsize=64)
    def reader():
        parser=ET.XMLPullParser(events=('start','end'));parser.feed('<stream>');depth=0;root=None;size=0
        try:
            while data:=sys.stdin.buffer.read1(4096):
                if b'<!' in data: raise ValueError('XML no permitido.')
                size+=len(data)
                if size>65536: raise ValueError('Mensaje INDI demasiado grande.')
                parser.feed(data)
                for event,element in parser.read_events():
                    if event=='start':
                        depth+=1
                        if depth==1: root=element
                    else:
                        if depth==2: inbox.put(element,timeout=2);root.remove(element);size=0
                        depth-=1
        except Exception as exc: print(str(exc),file=sys.stderr)
        finally: inbox.put(None)
    threading.Thread(target=reader,daemon=True).start();driver=Driver()
    try:
        while True:
            try:
                item=inbox.get(timeout=.05)
                if item is None: break
                driver.process(item)
            except queue.Empty: pass
            driver.tick()
    finally: driver.disconnect()

if __name__=='__main__': main()
