"""Produce the compact CC-BY-SA catalogue shipped with the application."""
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'build/astro-python'))
from astroall.catalog import normalized
from astroall.geometry import parse_angle
SOURCE=ROOT/'build/references03'
DEST=ROOT/'astroall/data'
DEST.mkdir(parents=True,exist_ok=True)

SPANISH={1:'Nebulosa del Cangrejo',8:'Nebulosa de la Laguna',13:'Gran cúmulo de Hércules',16:'Nebulosa del Águila',
 17:'Nebulosa Omega',20:'Nebulosa Trífida',27:'Nebulosa Dumbbell',31:'Galaxia de Andrómeda',33:'Galaxia del Triángulo',
 42:'Gran nebulosa de Orión',44:'Cúmulo del Pesebre',45:'Las Pléyades',51:'Galaxia del Remolino',57:'Nebulosa del Anillo',
 63:'Galaxia del Girasol',64:'Galaxia del Ojo Negro',81:'Galaxia de Bode',82:'Galaxia del Cigarro',104:'Galaxia del Sombrero'}
EXTRA={'NGC7000':'Nebulosa Norteamérica','NGC1499':'Nebulosa California','NGC6960':'Velo occidental',
       'NGC6992':'Velo oriental','IC1805':'Nebulosa del Corazón','IC1848':'Nebulosa del Alma','B033':'Cabeza de Caballo'}
def number(text):
    try: return float(text) if str(text).strip() else None
    except ValueError: return None
def names_for(prefix,text):
    return ' '.join(prefix+part.strip() for part in str(text).split(',') if part.strip())

path=DEST/'catalog.sqlite3'
temporary=DEST/'catalog.new.sqlite3'
if temporary.exists(): temporary.unlink()
connection=sqlite3.connect(temporary)
connection.executescript('''
CREATE TABLE objects(identifier TEXT PRIMARY KEY,name TEXT NOT NULL,ra_deg REAL NOT NULL,dec_deg REAL NOT NULL,
 kind TEXT NOT NULL,constellation TEXT NOT NULL,magnitude REAL,major_arcmin REAL,minor_arcmin REAL,position_angle REAL,
 messier INTEGER,aliases TEXT NOT NULL,source TEXT NOT NULL,search_key TEXT NOT NULL);
CREATE INDEX object_position ON objects(dec_deg,ra_deg);
CREATE INDEX object_messier ON objects(messier);
CREATE INDEX object_kind ON objects(kind);
CREATE TABLE stars(identifier INTEGER PRIMARY KEY,name TEXT,ra_deg REAL NOT NULL,dec_deg REAL NOT NULL,
 magnitude REAL NOT NULL,color_index REAL,pm_ra_mas_year REAL,pm_dec_mas_year REAL);
CREATE INDEX star_position ON stars(dec_deg,ra_deg);
CREATE INDEX star_magnitude ON stars(magnitude);
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
''')
messier=set();skipped=0
for filename in ('NGC.csv','addendum.csv'):
    with (SOURCE/filename).open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream,delimiter=';'):
            if row['Type'] in ('Dup','NonEx') or not row['RA'] or not row['Dec']:
                skipped+=1;continue
            try:
                ra,dec=parse_angle(row['RA'],hours=True),parse_angle(row['Dec'])
            except ValueError:
                skipped+=1;continue
            m=int(row['M']) if row['M'].isdigit() else None
            if row['Name']=='NGC5866': m=102  # Traditional M102 identification; see provenance below.
            if m: messier.add(m)
            identifier=row['Name']
            name=('Galaxia del Huso · M102 (identificación tradicional)' if m==102 else SPANISH.get(m,EXTRA.get(identifier,''))) or row['Common names'].split(',')[0].strip() or identifier
            aliases=' '.join((row['Common names'],row['Identifiers'],names_for('NGC',row['NGC']),names_for('IC',row['IC']),f'M{m}' if m else ''))
            vmag=number(row['V-Mag'])
            values=(identifier,name,ra,dec,row['Type'],row['Const'],vmag if vmag is not None else number(row['B-Mag']),
                    number(row['MajAx']),number(row['MinAx']),number(row['PosAng']),m,aliases,'OpenNGC',
                    normalized(' '.join((identifier,name,aliases,row['Const']))))
            connection.execute('INSERT INTO objects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',values)

from astropy.coordinates import SkyCoord
import astropy.units as u
center=SkyCoord(l=0*u.deg,b=0*u.deg,frame='galactic').icrs
region=('REGION_GC','Centro de la Vía Láctea',float(center.ra.deg),float(center.dec.deg),'Region','Sgr',None,1200.0,600.0,0.0,
        None,'Centro galáctico Vía Láctea Galactic center Sagittarius','Región definida por l=0°, b=0° (IAU)',normalized('Centro de la Vía Láctea Centro galáctico Galactic center Sagittarius REGION_GC'))
connection.execute('INSERT INTO objects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',region)
with (SOURCE/'hygdata.csv').open(encoding='utf-8-sig',newline='') as stream:
    for row in csv.DictReader(stream):
        mag=number(row['mag'])
        if row['id']=='0' or mag is None or mag>6.5: continue
        ra,dec=number(row['ra']),number(row['dec'])
        if ra is None or dec is None: continue
        connection.execute('INSERT INTO stars VALUES (?,?,?,?,?,?,?,?)',
                           (int(row['id']),row['proper'] or row['bf'].strip(),ra*15,dec,mag,number(row['ci']),number(row['pmra']),number(row['pmdec'])))
source=json.loads((SOURCE/'catalog-sources.json').read_text(encoding='utf-8'))
metadata={'created_utc':datetime.now(timezone.utc).isoformat(),'license':'CC-BY-SA-4.0',
          'attribution':'OpenNGC: Mattia Verga and contributors. HYG 4.1: David Nash / Astronexus.',
          'adaptation':'Filtered valid OpenNGC positions; Spanish aliases; HYG stars to magnitude 6.5; SQLite indexes.',
          'coordinates':'Equatorial J2000; HYG epoch 2000.0. Stars are chart references, not an astrometric solving index.',
          'objects':connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],
          'stars':connection.execute('SELECT COUNT(*) FROM stars').fetchone()[0],
          'messier_objects':len(messier),'messier_missing':sorted(set(range(1,111))-messier),
          'm102_note':'M102 uses the traditional NGC5866 identification; OpenNGC leaves that Messier cross-reference blank.',
          'm102_reference':'https://science.nasa.gov/mission/hubble/science/explore-the-night-sky/hubble-messier-catalog/messier-102/',
          'upstream':source,'skipped_invalid_or_duplicate':skipped}
assert not metadata['messier_missing'],metadata['messier_missing']
for key,value in metadata.items(): connection.execute('INSERT INTO metadata VALUES (?,?)',(key,json.dumps(value,ensure_ascii=False)))
connection.commit();connection.execute('VACUUM');connection.close()
temporary.replace(path)
shutil.copyfile(SOURCE/'CC-BY-SA-4.0.txt',DEST/'LICENSE-DATA-CC-BY-SA-4.0.txt')
(DEST/'catalog-sources.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
(DEST/'README-DATA.txt').write_text(metadata['attribution']+'\nData and adapted database: CC BY-SA 4.0.\n'+metadata['adaptation']+'\nhttps://github.com/mattiaverga/OpenNGC\nhttps://github.com/astronexus/HYG-Database\nhttps://creativecommons.org/licenses/by-sa/4.0/\n',encoding='utf-8')
print(json.dumps({key:metadata[key] for key in ('objects','stars','messier_objects','messier_missing')},indent=2))
print('Catalogue bytes:',path.stat().st_size,'SHA256:',hashlib.sha256(path.read_bytes()).hexdigest())
