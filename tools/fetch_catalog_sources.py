"""Obtain the exact catalogue inputs declared with the distributed database."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def fetch(verify_cache=False):
    upstream=json.loads((ROOT/'astroall/data/catalog-sources.json').read_text(encoding='utf-8'))['upstream']
    dest=ROOT/'build/references03';dest.mkdir(parents=True,exist_ok=True)
    for item in upstream['files']:
        name=item['file']
        if Path(name).name!=name or not item['url'].startswith('https://raw.githubusercontent.com/'):
            raise ValueError('Ruta o fuente de catálogo no admitida.')
        path=dest/name
        if path.is_symlink():raise ValueError('El destino es un enlace; no se modificó.')
        if not path.exists():
            if verify_cache:raise FileNotFoundError('Falta en caché: '+name)
            request=urllib.request.Request(item['url'],headers={'User-Agent':'Astro-One4All-catalog-source'})
            with urllib.request.urlopen(request,timeout=90) as source:data=source.read(100*1024*1024+1)
            if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
                raise RuntimeError('La descarga no coincide: '+name)
            path.write_bytes(data)
        data=path.read_bytes()
        if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            raise RuntimeError('El archivo no coincide; se conservó para revisarlo: '+name)
        print('Verificado:',name)
    (dest/'catalog-sources.json').write_text(json.dumps(upstream,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify-cache',action='store_true')
    fetch(parser.parse_args().verify_cache)
