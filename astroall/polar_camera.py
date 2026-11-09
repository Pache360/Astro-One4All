"""Image-based polar alignment. No serial ports or motor commands.

Three complete WCS orientations determine a common RA rotation axis, including
when the image centre is at the pole. Later WCS orientations transport that axis
in the unchanged camera frame. DEC, camera mounting and optics must remain fixed.
"""
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import math
from .polar import axis_report,horizon_vector
from .solve import SolvedFrame


def local_frame(utc,latitude,longitude,elevation=0):
    import astropy.units as u
    from astropy.coordinates import AltAz,EarthLocation
    from astropy.time import Time
    from .earthtime import configure_iers
    if not all(math.isfinite(v) for v in (latitude,longitude,elevation)) or not -90<=latitude<=90 or not -180<=longitude<=180 or not -500<=elevation<=10000:
        raise ValueError('Revisa la ubicación y altitud guardadas en Configuración.')
    instant=datetime.fromisoformat(str(utc).replace('Z','+00:00'))
    if instant.tzinfo is None:raise ValueError('La foto necesita una hora UTC con zona explícita.')
    configure_iers()
    return AltAz(obstime=Time(instant.astimezone(timezone.utc)),
                 location=EarthLocation.from_geodetic(longitude*u.deg,latitude*u.deg,elevation*u.m),pressure=0*u.hPa)


def orientation(solution,utc,latitude,longitude,elevation=0):
    import numpy as np
    cx,cy=(solution.width-1)/2,(solution.height-1)/2
    sky=solution.sky([cx,cx+1],[cy,cy]).transform_to(local_frame(utc,latitude,longitude,elevation))
    z,near=sky.cartesian.xyz.value.T
    z=z/np.linalg.norm(z);x=near-np.dot(near,z)*z;x=x/np.linalg.norm(x)
    return np.column_stack((x,np.cross(z,x),z))


def angle(a,b):
    import numpy as np
    return math.degrees(math.atan2(float(np.linalg.norm(np.cross(a,b))),float(np.dot(a,b))))


def rotation_angle(matrix):
    import numpy as np
    return math.degrees(math.acos(float(np.clip((np.trace(matrix)-1)/2,-1,1))))


def fit_axis(bases,latitude):
    import numpy as np
    if len(bases)!=3:raise ValueError('Primero mide las tres posiciones de AR.')
    bases=[np.asarray(b,dtype=float) for b in bases]
    if any(b.shape!=(3,3) or not np.isfinite(b).all() or not np.allclose(b.T@b,np.eye(3),atol=1e-5) or np.linalg.det(b)<.999 for b in bases):
        raise ValueError('Orientación de cámara inválida.')
    turns=[rotation_angle(bases[i]@bases[i-1].T) for i in (1,2)]
    if min(turns)<10:raise ValueError('Gira un poco más SOLO AR: faltan al menos 10° entre posiciones. Recomendado: 15–30°, respetando el recorrido libre.')
    rotations=[b@bases[0].T for b in bases[1:]]
    _,singular,vh=np.linalg.svd(np.vstack([r-np.eye(3) for r in rotations]))
    if singular[1]<.1:raise ValueError('Los giros no separan bien los puntos. Vuelve a medir.')
    axis=vh[-1];target=np.array(horizon_vector(0 if latitude>=0 else 180,abs(latitude)))
    if np.dot(axis,target)<0:axis=-axis
    residual=math.sqrt(sum(angle(axis,r@axis)**2 for r in rotations)/2)*60
    if residual>5 or singular[-1]/singular[1]>.02:
        raise ValueError('Las fotos no describen un único eje de AR. Repite sin mover DEC, cámara, lente ni base; revisa enfoque y flexiones.')
    report=axis_report(axis,latitude)
    report.update(axis_vector=axis.tolist(),camera_axis=(bases[-1].T@axis).tolist(),
                  rotation_degrees=turns,fit_residual_arcmin=residual)
    return report


def optical_signature(solution):
    import numpy as np
    matrix=solution.wcs().pixel_scale_matrix
    return (solution.width,solution.height,float(np.linalg.det(matrix)))


def compatible(reference,current):
    a,b=optical_signature(reference),optical_signature(current)
    if a[:2]!=b[:2] or a[2]*b[2]<=0 or not .94<=abs(b[2]/a[2])<=1.06:
        raise ValueError('Cambió el tamaño, orientación especular o escala de la cámara. Reinicia la medición con la misma focal y cámara.')


def project_sky(solution,sky):
    from astropy.wcs.utils import skycoord_to_pixel
    centre=solution.sky((solution.width-1)/2,(solution.height-1)/2)
    if float(centre.separation(sky).deg)>85:return None
    try:
        x,y=map(float,skycoord_to_pixel(sky,solution.wcs(),origin=0,mode='all'))
        if not math.isfinite(x+y):return None
        return {'x':x,'y':y,'inside':0<=x<solution.width and 0<=y<solution.height}
    except Exception:return None


def reticle(solution,utc,latitude,longitude,elevation,axis=None):
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    frame=local_frame(utc,latitude,longitude,elevation)
    pole=SkyCoord(az=(0 if latitude>=0 else 180)*u.deg,alt=abs(latitude)*u.deg,frame=frame).icrs
    result={'pole':project_sky(solution,pole),'axis':None,'polaris':None,'rings':[],
            'width':solution.width,'height':solution.height}
    # Angular circles are projected through the solved WCS, not a fixed pixel
    # scale or an assumed orientation of the camera on the mount.
    from astropy.wcs.utils import skycoord_to_pixel
    import numpy as np
    centre=solution.sky((solution.width-1)/2,(solution.height-1)/2)
    wcs=solution.wcs()
    for radius in (.25,.5,1):
        sky=pole.directional_offset_by(np.arange(0,361,6)*u.deg,radius*u.deg)
        try:
            x,y=skycoord_to_pixel(sky,wcs,origin=0,mode='all')
            visible=centre.separation(sky).deg<85
            points=[[float(a),float(b)] if good and math.isfinite(a+b) else None for a,b,good in zip(x,y,visible)]
        except Exception:points=[None]*61
        result['rings'].append({'radius_deg':radius,'points':points})
    if latitude>=0:
        # SIMBAD ICRS J2000, reference marker only (not a centroid measurement).
        polaris=SkyCoord('02h31m49.09456s','+89d15m50.7923s',frame='icrs')
        result['polaris']=project_sky(solution,polaris)
    if axis is not None:
        az=math.degrees(math.atan2(axis[1],axis[0]))%360;alt=math.degrees(math.asin(max(-1,min(1,axis[2]))))
        result['axis']=project_sky(solution,SkyCoord(az=az*u.deg,alt=alt*u.deg,frame=frame).icrs)
    return result


def instructions(report):
    alt,az=report['alt_adjustment_deg'],report['az_adjustment_deg']
    def amount(degrees):
        minutes=abs(degrees)*60
        return f'{minutes:.1f}′' if minutes<60 else f'{abs(degrees):.2f}°'
    vertical='Altura: sin ajuste apreciable.' if abs(alt)*60<.5 else f"{'Sube' if alt>0 else 'Baja'} el eje de la base {amount(alt)}."
    # Azimuth increases N→E→S→W. Near the southern pole the east/west sense
    # reverses. Avoid knob/left-right claims without a mechanical calibration.
    north=math.cos(math.radians(report['estimated_axis_az_deg']))>=0
    east=(az>0)==north
    north_pole=report.get('target_axis_az_deg',0)==0
    left=east!=north_pole
    horizontal='Azimut: sin ajuste apreciable.' if abs(az)*60<.5 else f"Gira la base a la {'izquierda' if left else 'derecha'} {amount(az)} ({'este' if east else 'oeste'}), mirando hacia el polo."
    return [vertical,horizontal,'Haz movimientos pequeños y vuelve a medir. No cambies DEC, la cámara ni el zoom.']


@dataclass
class PolarSample:
    solution: SolvedFrame
    utc: str
    jpeg: str
    source: str
    basis: list
    mount_dec: float | None = None


class PolarSession:
    """Bounded session in memory. Never reuses calibration after a new launch."""
    def __init__(self):
        self.samples=[];self.last=None;self.result=None;self.overlay=None
        self.site=None;self.error=None;self.revision=0

    def reset(self):self.__init__()

    def accept(self,sample,site):
        import numpy as np
        if self.site is not None and tuple(site)!=tuple(self.site):raise ValueError('La ubicación cambió. Reinicia los tres puntos.')
        if self.samples:
            ref=self.samples[-1]
            if ref.source!=sample.source:raise ValueError('Cambió la cámara. Reinicia la medición.')
            compatible(ref.solution,sample.solution)
            if ref.mount_dec is not None and sample.mount_dec is not None and abs(ref.mount_dec-sample.mount_dec)>.05:
                raise ValueError('DEC cambió desde la referencia. Reinicia los tres puntos; durante el ajuste usa solo la base.')
            if len(self.samples)<3 and rotation_angle(np.array(sample.basis)@np.array(ref.basis).T)<10:
                raise ValueError('Falta giro de AR. Gira otro tramo (15–30° recomendado) y vuelve a medir. Los puntos anteriores se conservan.')
        candidates=self.samples+[sample] if len(self.samples)<3 else self.samples
        result=None
        if len(candidates)==3:
            if len(self.samples)<3:result=fit_axis([s.basis for s in candidates],site[0])
            else:
                axis=np.array(sample.basis)@np.array(self.result['camera_axis'])
                result=dict(self.result,**axis_report(axis,site[0]),axis_vector=axis.tolist())
        axis=None if result is None else result['axis_vector']
        overlay=reticle(sample.solution,sample.utc,*site,axis=axis)
        self.samples=candidates;self.last=sample;self.site=tuple(site);self.result=result;self.overlay=overlay;self.error=None;self.revision+=1
        return self

    def diagnostic(self):
        return {'experimental':True,'points':len(self.samples),'revision':self.revision,'site':self.site,
                'samples':[asdict(s) for s in self.samples],'last':None if self.last is None else asdict(self.last),
                'result':self.result,'error':self.error,'hardware_accuracy_validated':False,'mount_commands_sent':False}
