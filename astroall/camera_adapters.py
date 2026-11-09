"""Extensible capture adapters. The Canon R50 keeps its dedicated path.

Other libgphoto2/PTP cameras use an explicitly experimental capability-based
adapter. No vendor-specific Bulb actuator or autofocus is guessed.
"""
from dataclasses import dataclass
from .camera import CanonSD,CameraError,require_raw_jpeg,shutter_seconds

@dataclass(frozen=True)
class CameraProfile:
    identifier:str
    matches:object
    factory:object

PROFILES=[]

def register(profile):
    if not profile.identifier or any(p.identifier==profile.identifier for p in PROFILES): raise ValueError('Perfil de cámara duplicado o inválido.')
    PROFILES.append(profile)

def adapter_for(camera,gp,report=None):
    model=camera.get_abilities().model
    profile=next((p for p in PROFILES if p.matches(model)),None)
    return (profile.factory if profile else GenericPTPSD)(camera,gp,report)

class GenericPTPSD(CanonSD):
    raw_suffixes=('.cr3','.cr2','.nef','.nrw','.arw','.sr2','.srf','.raf','.orf','.rw2','.rwl','.pef','.dng','.srw')
    aliases={'imageformat':('imageformat','imagequality'),'autoexposuremode':('autoexposuremode','exposuremode','expprogram'),
             'shutterspeed':('shutterspeed','shutterspeed2','exptime')}

    def config_name(self,name):
        for candidate in self.aliases.get(name,(name,)):
            try:super().widget(candidate);return candidate
            except CameraError:pass
        raise CameraError(f'La cámara no anuncia {name}; este perfil no permite adivinar su control.')

    def widget(self,name):return super().widget(self.config_name(name))
    def write_widget(self,name,value):return super().write_widget(self.config_name(name),value)

    def inspect(self):
        result=super().inspect()
        result['adapter']='PTP SD por capacidades · experimental, sin validación física de este modelo'
        result['bulb_supported']=False
        result['requirements']='Modo M, RAW+JPEG, destino Memory card y velocidad fija anunciados por la cámara.'
        result['autofocus_required']=False;result['guide_camera_required']=False
        return result

    def configure_exposure(self,exposure=None,iso=None,force_bulb=False):
        if force_bulb or (exposure is not None and float(exposure)>30):
            raise CameraError('Este modelo usa el módulo PTP experimental: primero prueba una velocidad fija de hasta 30 s. Bulb necesita un adaptador validado de su marca. No se disparó.')
        return super().configure_exposure(exposure,iso,False)

    def prepare(self,bulb=False):
        if str(self.widget('autoexposuremode').get_value()).strip().casefold() not in ('m','manual'):
            raise CameraError('Selecciona modo M/manual en la cámara. No se disparó.')
        quality=str(self.widget('imageformat').get_value())
        try:require_raw_jpeg(quality)
        except CameraError:
            # Explicit vendor RAW names and explicit JPEG quality labels only.
            import re
            parts=[p.strip().lower() for p in quality.split('+')]
            raw=bool(parts and re.search(r'\b(raw|nef|nrw|arw|raf|orf|rw2|pef|dng|srw)\b',parts[0]))
            jpeg=len(parts)==2 and any(x in parts[1] for x in ('jpeg','jpg','fine','normal','basic'))
            if not (raw and jpeg):raise CameraError('No se confirmó RAW + JPEG para este modelo. Configúralo en la cámara antes de capturar.')
        target=self.widget('capturetarget');choices=list(target.get_choices())
        card=next((c for c in choices if str(c).strip().lower() in ('memory card','sd card','tarjeta de memoria','tarjeta sd')),None)
        if card is None:raise CameraError('Este modelo no anuncia un destino seguro en su tarjeta. No se disparó.')
        self.write_widget('capturetarget',card)
        if str(self.widget('capturetarget').get_value())!=str(card):raise CameraError('La cámara no confirmó guardar en su tarjeta. No se disparó.')
        if not bulb:shutter_seconds(self.widget('shutterspeed').get_value())

register(CameraProfile('canon-r50-sd',lambda model:model=='Canon EOS R50',CanonSD))
