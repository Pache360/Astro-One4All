"""Bounded PHD2 JSON-RPC client; no camera images are requested."""
from collections import deque
import json
import math
import socket
import time

class GuideError(RuntimeError): pass

class PHD2Client:
    def __init__(self,host='127.0.0.1',port=4400):
        self.host,self.port=host,int(port)
        self.buffer=bytearray();self.request_id=0;self.pending={}
        self.events=deque(maxlen=160);self.steps=deque(maxlen=120)
        self.app_state='Unknown';self.settle_result=None;self.settling=False
        self.pixel_scale=None;self.last_event=None

    def __enter__(self):
        self.sock=socket.create_connection((self.host,self.port),timeout=3)
        self.sock.settimeout(.25)
        try: self.request('get_app_state')
        except Exception: self.sock.close();raise
        return self

    def __exit__(self,*args): self.sock.close()

    def ingest(self,data):
        self.buffer.extend(data)
        if len(self.buffer)>512*1024: raise GuideError('Respuesta PHD2 demasiado grande.')
        while b'\n' in self.buffer:
            line,_,remaining=self.buffer.partition(b'\n');self.buffer=bytearray(remaining)
            if not line.strip(): continue
            item=json.loads(line.decode('utf-8'))
            if not isinstance(item,dict): raise GuideError('Mensaje PHD2 inválido.')
            if 'Event' in item:
                self.events.append(item);self.last_event=time.monotonic()
                event=item['Event']
                state={'GuideStep':'Guiding','StarLost':'LostLock','Paused':'Paused','StartCalibration':'Calibrating',
                       'LoopingExposures':'Looping','LoopingExposuresStopped':'Stopped','GuidingStopped':'Stopped'}.get(event)
                if state: self.app_state=state
                if event=='AppState': self.app_state=item.get('State','Unknown')
                if event=='GuideStep':
                    ra,dec=item.get('RADistanceRaw'),item.get('DECDistanceRaw')
                    if all(isinstance(x,(int,float)) and math.isfinite(x) for x in (ra,dec)):
                        self.steps.append((float(ra),float(dec)))
                if event in ('SettleBegin','Settling'): self.settling=True
                if event=='SettleDone': self.settle_result=item;self.settling=False
            elif 'id' in item:
                if len(self.pending)>=32: raise GuideError('Demasiadas respuestas PHD2 pendientes.')
                self.pending[item['id']]=item

    def read(self):
        try: data=self.sock.recv(16384)
        except socket.timeout: return
        if not data: raise GuideError('PHD2 cerró la conexión.')
        self.ingest(data)

    def request(self,method,params=None,timeout=5):
        self.request_id+=1;identifier=self.request_id
        message={'method':method,'id':identifier}
        if params is not None: message['params']=params
        self.sock.sendall(json.dumps(message,separators=(',',':')).encode()+b'\r\n')
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if identifier in self.pending:
                response=self.pending.pop(identifier)
                if 'error' in response: raise GuideError(str(response['error'].get('message',response['error'])))
                result=response.get('result')
                if method=='get_app_state': self.app_state=str(result)
                if method=='get_pixel_scale' and isinstance(result,(int,float)) and math.isfinite(result) and result>0:
                    self.pixel_scale=float(result)
                return result
            self.read()
        raise GuideError(f'PHD2 no confirmó {method}; no se reenvió la orden.')

    @staticmethod
    def settle_parameters(pixels=1.5,seconds=5,timeout=90):
        if not all(math.isfinite(float(x)) for x in (pixels,seconds,timeout)) or not 0<pixels<=20 or not 0<=seconds<=60 or not seconds<timeout<=300:
            raise ValueError('Estabilización inválida: tolerancia en píxeles y tiempos en segundos.')
        return {'pixels':float(pixels),'time':int(seconds),'timeout':int(timeout)}

    def wait_settle(self,timeout,stop=None,progress=None):
        deadline=time.monotonic()+timeout+5
        while time.monotonic()<deadline:
            if stop and stop.is_set():
                self.request('stop_capture')
                raise GuideError('Guiado detenido por el usuario.')
            if self.settle_result is not None:
                if self.settle_result.get('Status')!=0:
                    raise GuideError('No se estabilizó el guiado: '+str(self.settle_result.get('Error','sin detalle')))
                return self.settle_result
            self.read()
            if progress: progress(self.snapshot())
        raise GuideError('No llegó SettleDone de PHD2; no se iniciará otra exposición.')

    def start_guiding(self,settle=None,recalibrate=False,stop=None,progress=None):
        settle=settle or self.settle_parameters()
        if not self.request('get_connected'): raise GuideError('Configura y conecta cámara y montura en el perfil de PHD2.')
        self.settle_result=None;self.settling=True
        self.request('guide',{'settle':settle,'recalibrate':bool(recalibrate)})
        return self.wait_settle(settle['timeout']+180,stop,progress)

    def dither(self,amount=2,ra_only=False,settle=None,stop=None,progress=None):
        if not math.isfinite(amount) or not 0<amount<=20: raise ValueError('Dither de 0 a 20 píxeles de cámara guía.')
        if self.request('get_app_state')!='Guiding': raise GuideError('El dither requiere guiado activo.')
        settle=settle or self.settle_parameters()
        self.settle_result=None;self.settling=True
        self.request('dither',{'amount':float(amount),'raOnly':bool(ra_only),'settle':settle})
        return self.wait_settle(settle['timeout'],stop,progress)

    def assert_guiding(self):
        state=self.request('get_app_state')
        if state!='Guiding' or self.settling:
            raise GuideError(f'El guiado no está listo ({state}); se detuvo la secuencia.')
        return True

    def snapshot(self):
        count=len(self.steps)
        ra=math.sqrt(sum(x*x for x,y in self.steps)/count) if count else None
        dec=math.sqrt(sum(y*y for x,y in self.steps)/count) if count else None
        scale=self.pixel_scale or 1.0
        return {'state':self.app_state,'settling':self.settling,'samples':count,
                'ra_rms':None if ra is None else ra*scale,'dec_rms':None if dec is None else dec*scale,
                'total_rms':None if ra is None else math.hypot(ra,dec)*scale,
                'unit':'arcsec' if self.pixel_scale else 'px','pixel_scale':self.pixel_scale,
                'steps':list(self.steps)}
