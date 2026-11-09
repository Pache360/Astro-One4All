"""OAT 1.13 protocol. One owner, explicit reply framing, no EEPROM commands."""
import math
import re
import time
from collections import deque
from .geometry import parse_angle

class ProtocolError(RuntimeError): pass

class OATProtocol:
    def __init__(self,serial): self.serial=serial;self.failed=False;self.transcript=deque(maxlen=40)

    def command(self,command,reply='none',timeout=1.5):
        if self.failed: raise ProtocolError('El enlace serie necesita reconectarse tras una respuesta incompleta.')
        if reply not in ('none','char','hash'): raise ValueError('Tipo de respuesta inválido.')
        record={'command':command,'framing':reply};self.transcript.append(record)
        try:
            self.serial.write(command.encode('ascii'));self.serial.flush()
            if reply=='none': return ''
            data=bytearray();deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                chunk=self.serial.read(1)
                if not chunk: continue
                data.extend(chunk)
                if len(data)>256: raise ProtocolError('Respuesta OAT demasiado larga.')
                if reply=='char' or chunk==b'#':
                    record['reply']=data.decode('ascii')
                    return record['reply'].rstrip('#')
            raise ProtocolError(f'Respuesta incompleta a {command}; no se repitió la orden.')
        except Exception as exc:
            record['error']=str(exc)
            if 'data' in locals(): record['partial_hex']=data.hex()
            self.failed=True
            # A stop has no reply, so it can still be attempted on a desynchronized link.
            try: self.serial.write(b':Q#');self.serial.flush()
            except Exception: pass
            raise

    def identify(self):
        product=self.command(':GVP#','hash');version=self.command(':GVN#','hash')
        return product,version

    @staticmethod
    def require_supported(product,version):
        if product!='OpenAstroTracker': raise ProtocolError(f'El perfil OAT recibió producto {product!r}. Selecciona su controlador específico.')
        match=re.fullmatch(r'[vV]?(\d+)\.(\d+)\.(\d+)',version)
        if not match or tuple(map(int,match.groups()))[:2]!=(1,13):
            raise ProtocolError(f'Identidad real: {product} {version}. Este controlador está validado por protocolo para la familia 1.13.x.')

    def status(self):
        ra=parse_angle(self.command(':GR#','hash'),hours=True)/15
        # OAT 1.13.22 writeDec emits +DD*MM'SS#, not +DD*MM:SS#.
        raw_dec=self.command(':GD#','hash')
        if not re.fullmatch(r'[+-]\d{2,3}\*\d{2}[:\x27]\d{2}',raw_dec):
            raise ProtocolError(f'Declinación OAT no reconocida: {raw_dec!r}.')
        dec=parse_angle(raw_dec.replace('*',':').replace("'",':'))
        raw=self.command(':GX#','hash');parts=raw.split(',')
        if len(parts)<2 or len(parts[1])<3: raise ProtocolError('Estado :GX# no reconocido; se requiere reconectar.')
        state=parts[0]
        return {'ra':ra,'dec':dec,'tracking':parts[1][2]=='T','slewing':state in ('SlewToTarget','FreeSlew','ManualSlew','Parking','Homing'),
                'parked':state=='Parked','state':state,'raw':raw}

    def tracking(self,enabled):
        if self.command(':MT1#' if enabled else ':MT0#','char')!='1': raise ProtocolError('OAT rechazó el seguimiento.')

    def goto(self,ra_hours,dec):
        if not all(math.isfinite(x) for x in (ra_hours,dec)) or not 0<=ra_hours<24 or not -90<=dec<=90: raise ValueError('Coordenadas fuera de rango.')
        seconds=round(ra_hours*3600)%(24*3600)
        ra=f'{seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}'
        seconds=round(abs(dec)*3600)
        decl=f'{"-" if dec<0 else "+"}{seconds//3600:02d}*{seconds%3600//60:02d}:{seconds%60:02d}'
        for command in (':Sr'+ra+'#',':Sd'+decl+'#'):
            if self.command(command,'char')!='1': raise ProtocolError('OAT rechazó las coordenadas; no se inició GoTo.')
        # OAT, like LX200, returns the single character ZERO for :MS# success.
        if self.command(':MS#','char')!='0': raise ProtocolError('OAT no aceptó GoTo; no se repitió.')

    def rate(self,index):
        if index not in range(4): raise ValueError('Velocidad inválida.')
        self.command(':R'+'GCMS'[index]+'#')

    def move(self,direction,enabled=True):
        if direction not in 'nsew' or len(direction)!=1: raise ValueError('Dirección inválida.')
        self.command((':'+'M' if enabled else ':Q')+direction+'#')

    def pulse(self,direction,milliseconds):
        if direction not in 'nsew' or len(direction)!=1 or not 0<milliseconds<=9999: raise ValueError('Pulso inválido.')
        self.command(f':Mg{direction}{int(milliseconds):04d}#')

    def abort(self): self.command(':Q#')
    def home(self): self.command(':hF#')
    def park(self): self.command(':hP#')
    def unpark(self):
        if self.command(':hU#','char')!='1': raise ProtocolError('OAT no confirmó salir de Park.')

