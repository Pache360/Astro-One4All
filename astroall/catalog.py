"""Small read-only, offline OpenNGC/HYG catalogue with bounded queries."""
from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path
import re
import sqlite3
import unicodedata

DATA=Path(__file__).parent/'data'
class ReadOnlyConnection(sqlite3.Connection):
    def __exit__(self,*args):
        try: return super().__exit__(*args)
        finally: self.close()
TYPES={'G':'Galaxia','GPair':'Par de galaxias','GTrpl':'Trío de galaxias','GGroup':'Grupo de galaxias',
       'OCl':'Cúmulo abierto','GCl':'Cúmulo globular','Cl+N':'Cúmulo y nebulosa','PN':'Nebulosa planetaria',
       'HII':'Región H II','DrkN':'Nebulosa oscura','EmN':'Nebulosa de emisión','Neb':'Nebulosa',
       'RfN':'Nebulosa de reflexión','SNR':'Remanente de supernova','*':'Estrella','**':'Estrella doble',
       '*Ass':'Asociación estelar','Nova':'Nova','Other':'Otro objeto','Region':'Región de cielo'}

def normalized(value):
    value=''.join(c for c in unicodedata.normalize('NFKD',str(value)) if not unicodedata.combining(c)).upper()
    value=re.sub(r'\b(NGC|IC|M)\s*0*(\d+)\b',lambda m:m[1]+str(int(m[2])),value)
    return ' '.join(re.sub(r'[^A-Z0-9]+',' ',value).split())

@dataclass(frozen=True)
class Target:
    identifier:str
    name:str
    ra_deg:float
    dec_deg:float
    kind:str='Other'
    constellation:str=''
    magnitude:float|None=None
    major_arcmin:float|None=None
    minor_arcmin:float|None=None
    position_angle:float|None=None
    messier:int|None=None
    aliases:str=''
    source:str='OpenNGC'

    def __post_init__(self):
        if not (math.isfinite(self.ra_deg) and 0<=self.ra_deg<360 and math.isfinite(self.dec_deg) and -90<=self.dec_deg<=90):
            raise ValueError('Coordenadas J2000 inválidas.')
        if not self.identifier or len(self.identifier)>160 or len(self.name)>300:
            raise ValueError('Nombre de objetivo inválido.')

    @property
    def label(self):
        prefix=f'M{self.messier} · ' if self.messier else ''
        return prefix+self.identifier+(' · '+self.name if self.name!=self.identifier else '')

class Catalog:
    def __init__(self,path=None):
        self.path=Path(path or DATA/'catalog.sqlite3')

    def connect(self):
        if not self.path.is_file():
            raise RuntimeError('Falta el catálogo local. Instala el paquete de datos de Astro One4All.')
        connection=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True,factory=ReadOnlyConnection)
        connection.row_factory=sqlite3.Row
        return connection

    def search(self,query='',kind='',limit=150,messier_only=False):
        limit=max(1,min(500,int(limit)))
        clauses=[]; args=[]
        for token in normalized(query).split():
            clauses.append("search_key LIKE ? ESCAPE '\\'")
            args.append('%'+token.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
        if kind:
            clauses.append('kind=?');args.append(kind)
        if messier_only: clauses.append('messier IS NOT NULL')
        where=' WHERE '+' AND '.join(clauses) if clauses else ''
        with self.connect() as connection:
            rows=connection.execute('SELECT '+','.join(Target.__dataclass_fields__)+' FROM objects'+where+
                                    ' ORDER BY messier IS NULL,messier,magnitude IS NULL,magnitude,identifier LIMIT ?',args+[limit]).fetchall()
        return [Target(**dict(row)) for row in rows]

    def get(self,identifier):
        with self.connect() as connection:
            row=connection.execute('SELECT '+','.join(Target.__dataclass_fields__)+' FROM objects WHERE identifier=?',(identifier,)).fetchone()
        if row is None: raise ValueError('No se encuentra ese objeto en el catálogo.')
        return Target(**dict(row))

    def region(self,ra,dec,radius,stars=False,limit=2000):
        if not all(math.isfinite(x) for x in (ra,dec,radius)) or not 0<radius<=180:
            raise ValueError('Región de cielo inválida.')
        low,high=max(-90,dec-radius),min(90,dec+radius)
        half_ra=180 if abs(dec)+radius>=89 else min(180,radius/max(.01,math.cos(math.radians(dec))))
        clauses=['dec_deg BETWEEN ? AND ?'];args=[low,high]
        if half_ra<180:
            start,end=(ra-half_ra)%360,(ra+half_ra)%360
            clauses.append('ra_deg BETWEEN ? AND ?' if start<=end else '(ra_deg>=? OR ra_deg<=?)')
            args.extend([start,end])
        table='stars' if stars else 'objects'
        limit=max(1,min(6000,int(limit)))
        with self.connect() as connection:
            rows=connection.execute(f'SELECT * FROM {table} WHERE '+ ' AND '.join(clauses)+
                                    ' ORDER BY magnitude IS NULL,magnitude LIMIT ?',args+[limit]).fetchall()
        return [dict(row) for row in rows]

    def metadata(self):
        with self.connect() as connection:
            return {row['key']:json.loads(row['value']) for row in connection.execute('SELECT * FROM metadata')}

def saved_targets_path(): return Path.home()/'.config/astroall/targets.json'

def saved_targets():
    try:
        value=json.loads(saved_targets_path().read_text(encoding='utf-8'))
        return [Target(**row) for row in value[:500]]
    except (OSError,ValueError,TypeError): return []

def save_target(target):
    targets={row.identifier:row for row in saved_targets()}
    targets[target.identifier]=target
    path=saved_targets_path();path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps([asdict(row) for row in list(targets.values())[-500:]],ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)
