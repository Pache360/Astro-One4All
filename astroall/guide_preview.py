"""One bounded monochrome INDI frame for confirming the selected USB camera."""
import base64
import io
from pathlib import Path
import time
import xml.etree.ElementTree as ET
from .indi import IndiClient
from .guide_camera import profile,selected_device,monochrome,diagnostic


class PreviewClient(IndiClient):
    max_receive_bytes=16*1024*1024
    def __init__(self,device,**kwargs):
        super().__init__(**kwargs);self.device=device;self.image=None;self.received=0;self.shape=None;self.image_format=None;self.blob_meta={}
    def ingest(self,data):
        self.received+=len(data)
        if self.received>self.max_receive_bytes: raise RuntimeError('La imagen guía supera el límite de memoria. Reduce la resolución en INDI.')
        super().ingest(data)
    def handle_blob(self,element):
        if element.get('device')!=self.device or self.image is not None: return
        for child in element:
            if child.get('name')!='CCD1': continue
            format=child.get('format')
            self.blob_meta={'format':format,'size':child.get('size')}
            if format not in ('.fits','.stream','.stream_jpg'): raise RuntimeError(f'Formato de imagen guía no compatible: {format}. El diagnóstico conserva el formato recibido.')
            payload=''.join((child.text or '').split())
            if len(payload)>12*1024*1024: raise RuntimeError('Imagen guía demasiado grande.')
            self.image=base64.b64decode(payload,validate=True)
            from .timekeeping import utc_now
            self.received_utc=utc_now()
            self.image_format=format
            if len(self.image)>8*1024*1024: raise RuntimeError('Imagen guía demasiado grande.')
            if format=='.stream':
                values=self.properties.get((self.device,'CCD_STREAM_FRAME'),self.properties.get((self.device,'CCD_FRAME'),{})).get('values',{})
                width=int(float(values.get('WIDTH',0)));height=int(float(values.get('HEIGHT',0)))
                if width<=0 or height<=0 or width*height!=len(self.image): raise RuntimeError('El vídeo no coincide con una imagen monocroma de un byte por píxel.')
                self.shape=(height,width)


def save_image(payload,destination,shape=None,jpeg=False,full_size=False):
    import numpy as np
    from astropy.io import fits
    from PIL import Image
    if jpeg:
        with Image.open(io.BytesIO(payload)) as source:
            if source.format!='JPEG' or source.width*source.height>4*1024*1024:raise RuntimeError('Se esperaba un fotograma JPEG de hasta 4 megapíxeles.')
            values=np.asarray(source.convert('L'),dtype=np.float32)
    elif shape is not None:
        data=np.frombuffer(payload,dtype='uint8').reshape(shape)
        if data.size>4*1024*1024: raise RuntimeError('La imagen guía supera 4 megapíxeles.')
        values=np.asarray(data,dtype=np.float32)
    else:
        with fits.open(io.BytesIO(payload),memmap=False) as hdus:
            data=hdus[0].data
            if data is None or data.ndim!=2 or data.size>4*1024*1024: raise RuntimeError('Se esperaba una imagen guía monocroma de hasta 4 megapíxeles.')
            values=np.asarray(data,dtype=np.float32)
    if not np.isfinite(values).all(): raise RuntimeError('La cámara entregó píxeles inválidos.')
    lo,hi=np.percentile(values,[1,99]);hi=max(float(hi),float(lo)+1)
    image=Image.fromarray(np.clip((values-lo)*255/(hi-lo),0,255).astype('uint8'))
    width,height=image.size
    if not full_size:image.thumbnail((640,480))
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    image.save(destination,format='JPEG',quality=82)
    return {'width':width,'height':height,'jpeg':str(destination)}


def stream_command(client,device,member):
    prop=client.get(device,'CCD_VIDEO_STREAM');values=prop['values']
    if member not in values:raise RuntimeError('El controlador no anuncia el modo de vídeo solicitado.')
    element=ET.Element('newSwitchVector',{'device':device,'name':'CCD_VIDEO_STREAM'})
    for name in values:ET.SubElement(element,'oneSwitch',{'name':name}).text='On' if name==member else 'Off'
    client.send(element)

def capture_preview(stop=None,exposure=.5,destination=None,full_size=False):
    import math
    if not math.isfinite(exposure) or not .1<=exposure<=15:raise ValueError('Tiempo de imagen guía inválido.')
    saved=profile();device=saved.get('indi_device')
    if not device: raise RuntimeError('Conecta primero la cámara elegida.')
    selected=selected_device(saved['path'])
    from .preferences import load
    if selected.get('role')=='internal' and not load()['show_internal_guide']:
        raise RuntimeError('Está seleccionada la cámara integrada. Busca equipo y elige la cámara USB para probar su imagen.')
    started=False;streaming=False;exposure_start=None
    try:
        with PreviewClient(device) as client:
            if client.get(device,'CONNECTION')['values'].get('CONNECT')!='On': raise RuntimeError('La cámara guía está desconectada.')
            actual=client.get(device,'DEVICE_PORT')['values']['PORT']
            if Path(actual).resolve()!=Path(saved['path']).resolve(): raise RuntimeError('INDI tiene abierta otra cámara. Selecciona y conecta la USB correcta.')
            stream=client.properties.get((device,'CCD_VIDEO_STREAM'),{}).get('values',{})
            if stream.get('STREAM_ON')=='On': raise RuntimeError('Detén las exposiciones de PHD2 antes de probar la imagen aquí.')
            if client.get(device,'CCD_EXPOSURE')['state']=='Busy': raise RuntimeError('La cámara ya está exponiendo. Espera a que termine.')
            monochrome(client,device)
            client.send(ET.Element('enableBLOB',{'device':device,'name':'CCD1'}),'Also')
            try:
                if 'STREAM_ON' in stream:
                    # Some real UVC drivers do not echo STREAM_ON, even while
                    # delivering frames. The actual frame is the confirmation.
                    streaming=True;stream_command(client,device,'STREAM_ON')
                else:
                    from .timekeeping import utc_now
                    started=True;exposure_start=utc_now();client.write(device,'CCD_EXPOSURE',{'CCD_EXPOSURE_VALUE':exposure},'Number')
                deadline=time.monotonic()+20
                while client.image is None and time.monotonic()<deadline:
                    if stop and stop.is_set():raise RuntimeError('Prueba de imagen detenida.')
                    client.collect(.2)
                    prop=client.get(device,'CCD_VIDEO_STREAM') if streaming else client.get(device,'CCD_EXPOSURE')
                    if prop.get('state')=='Alert':raise RuntimeError('El controlador rechazó la imagen: '+' · '.join(m['message'] for m in client.messages))
                if client.image is None: raise RuntimeError('La webcam no entregó una imagen en 20 s. El diagnóstico conserva su nombre y conexión.')
                result=save_image(client.image,destination or Path.home()/'.cache/astroall/guide-preview.jpg',client.shape,jpeg=getattr(client,'image_format',None)=='.stream_jpg',full_size=full_size)
                result.update(name=saved['name'],path=saved['path'])
                from datetime import timedelta
                from .timekeeping import utc_now
                received=getattr(client,'received_utc',utc_now())
                result['approx_mid_utc']=(received if streaming else exposure_start+timedelta(seconds=exposure/2)).isoformat()
                result['time_note']='Hora de recepción del vídeo; latencia USB sin calibrar.' if streaming else 'Mitad estimada de la exposición; latencia USB sin calibrar.'
                result['source_format']=getattr(client,'image_format',None)
                mode=saved.get('video_mode',{})
                if mode and [result['width'],result['height']]!=[mode['width'],mode['height']]:
                    raise RuntimeError('El tamaño de la imagen recibida cambió respecto a la resolución confirmada. Se detuvo la vista previa para evitar una imagen deformada.')
                diagnostic(stage='image_received',preview={k:v for k,v in result.items() if k!='jpeg'},blob=getattr(client,'blob_meta',{}),indi_snapshot=client.snapshot(device),error=None)
                return result
            finally:
                client.send(ET.Element('enableBLOB',{'device':device,'name':'CCD1'}),'Never')
                if streaming:
                    stream_command(client,device,'STREAM_OFF')
                    end=time.monotonic()+2
                    while time.monotonic()<end:
                        client.collect(.2)
                        if client.get(device,'CCD_VIDEO_STREAM')['values'].get('STREAM_OFF')=='On':break
                    else:diagnostic(cleanup_warning='Se envió detener vídeo; el controlador no confirmó su estado.')
                elif started and client.image is None and client.get(device,'CCD_EXPOSURE')['state']=='Busy' and (device,'CCD_ABORT_EXPOSURE') in client.properties:
                    client.switch(device,'CCD_ABORT_EXPOSURE','ABORT')
    except Exception as exc:
        diagnostic(stage='preview_error',error=str(exc),selected=selected,blob=getattr(client,'blob_meta',{}) if 'client' in locals() else {},indi_snapshot=client.snapshot(device) if 'client' in locals() else {},driver_messages=list(client.messages) if 'client' in locals() else []);raise
