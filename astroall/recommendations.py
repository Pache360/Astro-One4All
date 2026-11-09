"""Conservative, editable starting plans; not a sky-noise/SNR optimizer."""
import math
from .optics import field_width

SENSORS={'APS-C Canon':(22.3,14.9),'APS-C':(23.5,15.6),'Full Frame':(36.,24.)}

def recommend(target,sensor='APS-C Canon',guided=False):
    if sensor not in SENSORS: raise ValueError('Selecciona un formato de sensor.')
    width,height=SENSORS[sensor]
    measured=bool(target.major_arcmin and target.major_arcmin>0)
    major=(target.major_arcmin/60) if measured else (5 if target.kind=='Region' else 2 if target.kind in ('HII','Neb','EmN','DrkN','SNR') else 1)
    minor=(target.minor_arcmin/60) if target.minor_arcmin and target.minor_arcmin>0 else major
    major,minor=max(major,minor),min(major,minor)
    # 35% room around the catalogue extent; the physical rotation remains manual.
    limit=min(width/(2*math.tan(math.radians(min(170,major*1.35))/2)),height/(2*math.tan(math.radians(min(170,minor*1.35))/2)))
    candidates=[10,18,24,35,45,50,55,85,100,135,200,250] if sensor!='Full Frame' else [14,20,24,35,50,85,135,200,300,400,600,800]
    focal=max((f for f in candidates if f<=limit),default=min(candidates))
    if sensor=='Full Frame':
        lens='50 mm f/1.8' if focal==50 else f'Lente de {focal} mm con cobertura Full Frame'
    else:
        lens='TTArtisan 10 mm f/2' if focal==10 else '18–45 mm' if focal<=45 else '50 mm f/1.8' if focal==50 else '55–250 mm'
    seconds=30 if focal<=24 else 20 if focal<=55 else 10 if focal<=135 else 5
    if guided: seconds=30  # long Bulb requires a separate physical validation.
    minutes=30 if target.kind in ('OCl','GCl','*','**') else 60
    count=math.ceil(minutes*60/seconds)
    notes=['Propuesta inicial: ajusta tras una foto de prueba e histograma; depende del cielo y del seguimiento.',
           'Ajusta focal, apertura y enfoque físicamente. RAW + JPG en la SD de la cámara.']
    if not measured: notes.append('Sin tamaño de catálogo: campo estimado, comprueba el encuadre.')
    if focal<limit/2: notes.append('Objeto pequeño para esta focal: considera recorte o mayor focal.')
    if focal>limit: notes.append('El objeto no cabe completo: reduce focal o prepara un mosaico.')
    if sensor=='Full Frame': notes.append('18–45 RF-S, 55–250 EF-S y TTArtisan APS-C no cubren Full Frame; usa un lente compatible.')
    return {'sensor':sensor,'sensor_w':width,'sensor_h':height,'lens':lens,'focal':focal,'exposure':seconds,'count':count,
            'iso':'800','delay':3,'minutes':minutes,'guided':bool(guided),'field_w':field_width(width,focal),
            'field_h':field_width(height,focal),'notes':notes}

def describe(plan):
    return f"{plan['sensor']}: {plan['lens']} a {plan['focal']} mm · {plan['count']} × {plan['exposure']} s · ISO {plan['iso']} · {plan['minutes']} min de integración"

def capture_proposal(target,sensor,focal,guided=False,settings=None):
    plan=recommend(target,sensor,guided);focal=float(focal)
    if not math.isfinite(focal) or not 1<=focal<=5000:raise ValueError('Escribe la focal real del lente, entre 1 y 5000 mm.')
    plan['recommended_focal']=plan['focal'];plan['focal']=focal
    plan['exposure']=30 if guided or focal<=24 else 20 if focal<=55 else 10 if focal<=135 else 5
    if settings:
        plan.update(minutes=settings['minutes'],iso=settings['iso'],delay=settings['delay'])
    plan.update(count=math.ceil(plan['minutes']*60/plan['exposure']),field_w=field_width(plan['sensor_w'],focal),field_h=field_width(plan['sensor_h'],focal))
    return plan
