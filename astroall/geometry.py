"""Pole-aware sky geometry, gnomonic atlas projection and bounded mosaics."""
import math
from .solve import Position,separation_arcsec

def parse_angle(text,hours=False):
    value=str(text).strip().replace('−','-')
    if ':' not in value:
        result=float(value)
    else:
        parts=value.lstrip('+-').split(':')
        if len(parts) not in (2,3): raise ValueError('Usa horas:minutos:segundos o grados:minutos:segundos.')
        a,b=float(parts[0]),float(parts[1]);c=float(parts[2]) if len(parts)==3 else 0
        if not 0<=b<60 or not 0<=c<60: raise ValueError('Minutos y segundos deben ser menores que 60.')
        result=(-1 if value.startswith('-') else 1)*(a+b/60+c/3600)
    if not math.isfinite(result): raise ValueError('Coordenada no finita.')
    if hours:
        if not 0<=result<24: raise ValueError('AR en horas, desde 0 hasta menos de 24.')
        return result*15
    if not -90<=result<=90: raise ValueError('DEC debe estar entre −90 y 90 grados.')
    return result

def format_ra(degrees):
    total=round((degrees%360)/15*3600,1)%(24*3600)
    h=int(total//3600);m=int(total%3600//60);s=total%60
    return f'{h:02d}:{m:02d}:{s:04.1f}'

def format_dec(degrees):
    total=round(abs(degrees)*3600,1)
    return f'{"-" if degrees<0 else "+"}{int(total//3600):02d}:{int(total%3600//60):02d}:{total%60:04.1f}'

def vector(position):
    a,d=math.radians(position.ra_deg),math.radians(position.dec_deg)
    return (math.cos(d)*math.cos(a),math.cos(d)*math.sin(a),math.sin(d))

def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def from_vector(v):
    norm=math.sqrt(dot(v,v))
    if not math.isfinite(norm) or norm<1e-12: raise ValueError('Vector de cielo inválido.')
    return Position(math.degrees(math.atan2(v[1],v[0]))%360,math.degrees(math.asin(max(-1,min(1,v[2]/norm)))))

def basis(center):
    a,d=math.radians(center.ra_deg),math.radians(center.dec_deg)
    return vector(center),(-math.sin(a),math.cos(a),0),(-math.sin(d)*math.cos(a),-math.sin(d)*math.sin(a),math.cos(d))

def project(position,center):
    c,e,n=basis(center);v=vector(position);den=dot(c,v)
    if den<=1e-8: return None
    return dot(e,v)/den,dot(n,v)/den

def offset(center,east_deg,north_deg):
    if not all(math.isfinite(x) and abs(x)<85 for x in (east_deg,north_deg)):
        raise ValueError('El mosaico excede el campo permitido por esta proyección.')
    c,e,n=basis(center);x,y=math.tan(math.radians(east_deg)),math.tan(math.radians(north_deg))
    return from_vector(tuple(c[i]+x*e[i]+y*n[i] for i in range(3)))

def correction_target(mount_eod,solved_eod,target_eod,max_degrees=2):
    angle=separation_arcsec(solved_eod,target_eod)/3600
    if not 0<max_degrees<=10 or angle>max_degrees:
        raise ValueError(f'La corrección de {angle:.3f}° excede el límite de {max_degrees}°; no se envió movimiento.')
    if angle<1e-8: return mount_eod
    a,b,m=vector(solved_eod),vector(target_eod),vector(mount_eod)
    axis=cross(a,b);length=math.sqrt(dot(axis,axis))
    if length<1e-10: raise ValueError('No se puede calcular una corrección antipodal.')
    axis=tuple(x/length for x in axis);theta=math.radians(angle);axm=cross(axis,m)
    return from_vector(tuple(m[i]*math.cos(theta)+axm[i]*math.sin(theta)+axis[i]*dot(axis,m)*(1-math.cos(theta)) for i in range(3)))

def mosaic(center,width_deg,height_deg,rows=1,columns=1,overlap=.2,angle_deg=0):
    if not isinstance(rows,int) or not isinstance(columns,int) or not 1<=rows<=9 or not 1<=columns<=9:
        raise ValueError('El mosaico admite de 1 a 9 filas y columnas.')
    if not all(math.isfinite(x) for x in (width_deg,height_deg,overlap,angle_deg)) or not 0<width_deg<170 or not 0<height_deg<170 or not 0<=overlap<=.8:
        raise ValueError('Campo o solapamiento de mosaico inválido.')
    angle=math.radians(angle_deg);panels=[]
    for row in range(rows):
        sequence=range(columns) if row%2==0 else range(columns-1,-1,-1)
        for column in sequence:
            x=(column-(columns-1)/2)*width_deg*(1-overlap)
            y=((rows-1)/2-row)*height_deg*(1-overlap)
            p=offset(center,x*math.cos(angle)+y*math.sin(angle),-x*math.sin(angle)+y*math.cos(angle))
            panels.append({'panel':len(panels)+1,'row':row+1,'column':column+1,'ra_deg':p.ra_deg,'dec_deg':p.dec_deg,'angle_deg':angle_deg})
    return panels
