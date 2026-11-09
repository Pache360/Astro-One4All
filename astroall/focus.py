"""Bounded JPEG star detection and half-flux radius for manual focusing."""
from pathlib import Path
import math

def measure(path,max_stars=80):
    import numpy as np
    from PIL import Image
    path=Path(path)
    if path.suffix.lower() not in ('.jpg','.jpeg') or path.stat().st_size>16*1024*1024: raise ValueError('El enfoque usa un JPG de hasta 16 MB.')
    with Image.open(path) as source:
        if source.width*source.height>30_000_000: raise ValueError('JPG demasiado grande.')
        original=source.size;source.draft('RGB',(1600,1600));source.thumbnail((1600,1600))
        image=np.asarray(source.convert('L'),dtype=np.float32)
    scale=original[0]/image.shape[1];h,w=image.shape
    if min(h,w)<40: raise ValueError('Imagen demasiado pequeña para medir estrellas.')
    background=float(np.median(image));mad=float(np.median(np.abs(image-background)));noise=max(1,1.4826*mad)
    peak=image[1:-1,1:-1];mask=peak>background+max(10,6*noise)
    for dy,dx in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
        mask&=peak>image[1+dy:h-1+dy,1+dx:w-1+dx]
    ys,xs=np.nonzero(mask);order=np.argsort(image[ys+1,xs+1])[::-1][:2000]
    stars=[];radius=10
    yy,xx=np.mgrid[-radius:radius+1,-radius:radius+1]
    for index in order:
        x=int(xs[index]+1);y=int(ys[index]+1)
        if min(x,y,w-x-1,h-y-1)<=radius: continue
        if any((x-s['x'])**2+(y-s['y'])**2<radius**2 for s in stars): continue
        patch=image[y-radius:y+radius+1,x-radius:x+radius+1]
        if float(patch.max())>=250: continue
        border=np.concatenate((patch[0],patch[-1],patch[:,0],patch[:,-1]));local=float(np.median(border))
        flux=np.maximum(patch-local-1.5*noise,0);total=float(flux.sum())
        if total<200: continue
        cx=float((flux*xx).sum()/total);cy=float((flux*yy).sum()/total)
        distance=np.hypot(xx-cx,yy-cy);indices=np.argsort(distance.ravel());cumulative=np.cumsum(flux.ravel()[indices]);half=int(np.searchsorted(cumulative,total*.5));hfr=float(distance.ravel()[indices[min(half,len(indices)-1)]])
        if not .6<hfr<radius*.7: continue
        stars.append({'x':x,'y':y,'hfr':hfr,'flux':total})
        if len(stars)>=max_stars: break
    if len(stars)<3: raise ValueError('No se detectaron al menos 3 estrellas sin saturar. Ajusta exposición, ISO o enfoque.')
    values=np.array([s['hfr'] for s in stars]);median=float(np.median(values))
    return {'hfr_preview_px':median,'hfr_original_px':median*scale,'stars':len(stars),'preview_width':w,'preview_height':h,'scale':scale,
            'detections':stars,'background':background,'noise':noise,'note':'HFR aproximado en JPG; compara el mismo campo, focal, exposición y escala.'}
