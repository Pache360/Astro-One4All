"""Beginner polar wizard with a real solved-image reticle and manual adjustments."""
import json
import math
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from .polar_camera import PolarSession,instructions
from .timekeeping import load_settings,clock_snapshot
from .recommendations import SENSORS


def state(app):
    if not hasattr(app,'polar'):
        from .preferences import load
        pref=load()
        app.polar={'session':PolarSession(),'source':tk.StringVar(value='Cámara principal'),
                   'sensor':tk.StringVar(value=pref['sensor']),'focal':tk.StringVar(value=str(pref['focal'])),
                   'field':tk.StringVar(),'seconds':tk.StringVar(value='2'),'ready':tk.BooleanVar(value=False),
                   'auto':False,'config':None,'timer':None}
    return app.polar


def pause(app):
    if not hasattr(app,'polar'):return
    app.polar['auto']=False
    token=app.polar.get('timer')
    if token:
        try:app.root.after_cancel(token)
        except tk.TclError:pass
    app.polar['timer']=None


def mount_dec(app):
    try:
        return next(float(prop['values']['DEC']) for key,prop in getattr(app,'mount_snapshot',{}).items()
                    if key.endswith('/EQUATORIAL_EOD_COORD') and prop.get('values',{}).get('DEC') is not None)
    except (StopIteration,ValueError,TypeError):return None


def diagnostic(app):
    return state(app)['session'].diagnostic()


def save_diagnostic(session):
    path=Path.home()/'.local/state/astroall/polar.json';path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(session.diagnostic(),ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)


def page(app):
    app.polar_view=PolarView(app)


class PolarView:
    def __init__(self,app):
        self.app=app;self.state=state(app);self.session=self.state['session'];self.photo=None;self.image_key=None;self.image=None
        top,body=app.card(app.content,'Prepara · mide · ajusta','PUESTA EN ESTACIÓN CON IMÁGENES · EXPERIMENTAL')
        top.pack(fill='x')
        row=app.frame(body,'card');row.pack(fill='x')
        self.fields=[];self.columns={}
        for label,key,choices,width in [('Cámara','source',['Cámara principal','Cámara guía USB'],22),
                                        ('Sensor principal','sensor',list(SENSORS),15),('Focal real / mm','focal',None,7),
                                        ('Exposición / s','seconds',['1','2','3','5','10'],6),('Campo guía ° · opcional','field',None,9)]:
            col=app.frame(row,'card');col.pack(side='left',padx=(0,9))
            self.columns[key]=col
            app.label(col,label,size=8,color='muted').pack(anchor='w')
            field=ttk.Combobox(col,textvariable=self.state[key],values=choices,width=width,state='readonly' if key in ('source','sensor') else 'normal') if choices else ttk.Entry(col,textvariable=self.state[key],width=width)
            field.pack(fill='x',pady=(3,0))
            if key=='source':field.bind('<<ComboboxSelected>>',lambda e:self.render())
            if key!='seconds':self.fields.append((key,field))
        row=app.frame(body,'card');row.pack(fill='x',pady=(8,0))
        from .atlas_ui import site_window
        app.button(row,'Hora y ubicación',lambda:site_window(app)).pack(side='right')
        settings=load_settings();clock=clock_snapshot(dict(settings,longitude=None))
        lat,lon=settings.get('latitude'),settings.get('longitude')
        self.site_text=('Ubicación pendiente' if lat is None or lon is None else f'{lat:.4f}°, {lon:.4f}°')+' · UTC '+clock['utc'][:19].replace('T',' ')
        app.label(row,self.site_text,size=9,color='muted').pack(side='left')
        ttk.Checkbutton(body,text='Enfoque listo, equipo firme y fecha/hora comprobadas',variable=self.state['ready']).pack(anchor='w',pady=(6,0))
        area=app.frame(app.content);area.pack(fill='both',expand=True,pady=(12,0))
        outer,preview=app.card(area,'Tu cielo, con referencias reales','FOTO RESUELTA · RETÍCULA CELESTE')
        outer.pack(side='left',fill='both',expand=True,padx=(0,12))
        self.canvas=tk.Canvas(preview,bg=app.colors['preview'],highlightthickness=0,width=240,height=210)
        app.painted.append((self.canvas,'preview',None));self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        self.caption=tk.StringVar();app.label(preview,variable=self.caption,size=8,color='muted',wraplength=420,justify='left').pack(anchor='w',pady=(7,0))
        outer,side=app.card(area,'Un paso a la vez')
        outer.configure(width=288);outer.pack(side='left',fill='y');outer.pack_propagate(False)
        self.step=tk.StringVar();self.help=tk.StringVar();self.error=tk.StringVar();self.metric=tk.StringVar();self.directions=tk.StringVar()
        app.label(side,variable=self.step,size=12,bold=True,color='accent',wraplength=250,justify='left').pack(anchor='w')
        app.label(side,variable=self.help,size=9,wraplength=250,justify='left').pack(anchor='w',pady=(9,0))
        app.label(side,variable=self.metric,size=18,bold=True,color='success').pack(anchor='w',pady=(10,0))
        app.label(side,variable=self.directions,size=10,wraplength=250,justify='left').pack(anchor='w',pady=(5,0))
        self.primary=app.button(side,'Tomar punto 1 de 3',self.measure,primary=True);self.primary.pack(fill='x',pady=(12,5))
        self.repeat=app.button(side,'Activar refresco',self.toggle_auto);self.repeat.pack(fill='x',pady=3)
        app.button(side,'Reiniciar medición',self.reset).pack(fill='x',pady=3)
        app.label(side,variable=self.error,size=9,color='danger',wraplength=250,justify='left').pack(anchor='w',pady=(8,0))
        app.label(side,'Solo ajustas la base a mano.\nNo se envía GoTo ni se modifica el OAT.',size=8,color='muted',wraplength=250,justify='left').pack(side='bottom',anchor='w',pady=(6,0))
        self.render()

    def alive(self):
        return self.app.current_page=='polar' and getattr(self.app,'polar_view',None) is self and self.canvas.winfo_exists()

    def render(self):
        n=len(self.session.samples);result=self.session.result
        guide=self.state['source'].get()=='Cámara guía USB'
        for key in ('sensor','focal','field'):self.columns[key].pack_forget()
        for key in (('field',) if guide else ('sensor','focal')):
            self.columns[key].pack(side='left',padx=(0,9),before=self.columns['seconds'])
        for key,field in self.fields:field.configure(state='disabled' if n else 'readonly' if key in ('source','sensor') else 'normal')
        self.primary.configure(text=f'Tomar punto {n+1} de 3' if n<3 else 'Comprobar ajuste')
        self.repeat.configure(text='Detener refresco' if self.state['auto'] else 'Activar refresco')
        self.repeat.state(['!disabled'] if n==3 else ['disabled'])
        self.step.set('1 · Prepara tu equipo' if n==0 else f'2 · Medición {n} de 3' if n<3 else '3 · Acerca las dos marcas')
        self.help.set('Apunta la cámara a estrellas enfocadas, cerca de Polaris si la ves. La montura debe estar aproximadamente orientada al polo. Toma el primer punto.' if n==0 else
                      'Gira SOLO AR otro tramo con el mando LCD (15–30° si el recorrido lo permite). Espera a que deje de moverse y toma el siguiente punto. No ajustes la base todavía.' if n<3 else
                      'Mirando hacia el polo, ajusta altitud y azimut de la base. Mantén DEC, cámara y zoom fijos. Comprueba cada ajuste.')
        self.metric.set('' if result is None else f"{result['polar_error_arcmin']:.1f}′ aprox.")
        self.directions.set('' if result is None else '\n\n'.join(instructions(result)[:2]))
        error=self.session.error or '';self.error.set(error if len(error)<=200 else error[:197]+'…')
        if self.session.last:
            when=self.session.last.utc[11:19]
            self.caption.set(f'Última medición: {when} UTC · círculo: eje medido · cruz: polo celeste · Polaris: referencia aproximada.\nCada imagen se resuelve de nuevo. Las marcas fuera del encuadre se indican en el borde.')
        else:self.caption.set('Canon: cada medición guarda RAW + JPG en su SD. Solo se recibe el JPG.\nUSB: requiere estrellas suficientes; el tiempo de vídeo depende de la webcam. Precisión física pendiente de validar.')
        self.draw()

    def reset(self):
        if self.app.busy:self.app.write('Espera a que termine la medición antes de reiniciar.');return
        pause(self.app);self.session.reset();self.state['config']=None;self.image_key=None;self.image=None
        self.render();self.app.write('Medición polar reiniciada. Las fotos de la SD y la conexión OAT se conservan.')

    def toggle_auto(self):
        if self.state['auto']:
            pause(self.app);self.render();return
        if len(self.session.samples)!=3:return
        self.state['auto']=True;self.render();self.measure()

    def measure(self):
        token=self.state.get('timer')
        if token:
            try:self.app.root.after_cancel(token)
            except tk.TclError:pass
            self.state['timer']=None
        if self.app.busy:
            self.app.write('Hay una tarea en curso. Espera antes de medir.');pause(self.app);self.render();return
        from .polar_capture import configuration,measure
        try:
            config=configuration('main' if self.state['source'].get()=='Cámara principal' else 'guide',
                                 self.state['sensor'].get(),self.state['focal'].get(),self.state['field'].get(),
                                 self.state['seconds'].get(),self.state['ready'].get())
            frozen=self.state['config']
            if frozen and any(config[key]!=frozen[key] for key in ('source','identity','width_deg','site')):
                raise ValueError('Cambió el equipo o la ubicación. Reinicia la medición para obtener una referencia nueva.')
        except Exception as exc:
            self.session.error=str(exc);pause(self.app);self.render();return
        dec=mount_dec(self.app)
        def operation():
            try:return {'sample':measure(config,self.app.stop,dec)}
            except Exception as exc:return {'error':str(exc)}
        def done(value):
            try:
                if 'error' in value:raise RuntimeError(value['error'])
                self.session.accept(value['sample'],config['site']);self.state['config']=config
                if self.session.result:self.app.write(f"Polar: error estimado {self.session.result['polar_error_arcmin']:.1f}′. Ajuste físico de base, sin mover motores.")
                else:self.app.write(f'Polar: {len(self.session.samples)} de 3 puntos medidos. Se conserva la conexión de los equipos.')
            except Exception as exc:
                self.session.error=str(exc);pause(self.app);self.app.write('Medición polar: '+str(exc))
            try:save_diagnostic(self.session)
            except OSError as exc:self.app.write('No se pudo guardar el diagnóstico polar: '+str(exc))
            view=getattr(self.app,'polar_view',None)
            if view and view.alive():view.render()
            if self.state['auto'] and view and view.alive():
                self.state['timer']=self.app.root.after(3000,view.measure)
        self.app.task('Midiendo alineación polar · foto y plate solving…',operation,done)

    def draw(self):
        if not self.alive():return
        c=self.canvas;colors=self.app.colors;c.delete('all');w,h=max(c.winfo_width(),1),max(c.winfo_height(),1)
        sample=self.session.last;overlay=self.session.overlay
        if sample is None:
            cx,cy=w/2,h/2
            for r in (22,45,70):c.create_oval(cx-r,cy-r,cx+r,cy+r,outline=colors['border'])
            c.create_line(cx-83,cy,cx+83,cy,fill=colors['accent']);c.create_line(cx,cy-83,cx,cy+83,fill=colors['accent'])
            c.create_text(cx,cy+101,text='Aquí aparecerá tu foto del cielo.',fill=colors['muted'],font=(self.app.font,10))
            return
        try:
            from PIL import Image,ImageTk,ImageOps
            if self.image_key!=sample.jpeg:
                with Image.open(sample.jpeg) as source:
                    source.draft('RGB',(1100,800));source.thumbnail((1100,800));self.image=source.convert('RGB')
                self.image_key=sample.jpeg
            image=self.image.copy();image.thumbnail((w,h));iw,ih=image.size
            if self.app.night:image=ImageOps.colorize(ImageOps.grayscale(image),'#070000','#b65443')
            self.photo=ImageTk.PhotoImage(image);c.create_image(w/2,h/2,image=self.photo)
        except Exception:
            c.create_text(w/2,h/2,text='JPG no disponible; la medición se conserva.',fill=colors['muted']);return
        left,top=(w-iw)/2,(h-ih)/2;sx,sy=iw/overlay['width'],ih/overlay['height']
        def xy(point):return left+point[0]*sx,top+point[1]*sy
        for ring in overlay['rings']:
            points=ring['points']
            for a,b in zip(points,points[1:]):
                if a is None or b is None:continue
                a,b=xy(a),xy(b)
                if all(left-5<=p[0]<=left+iw+5 and top-5<=p[1]<=top+ih+5 for p in (a,b)):
                    c.create_line(*a,*b,fill=colors['muted'],dash=(3,5))
        locations={}
        for key,label,color in [('polaris','Polaris · referencia',colors['accent']),('pole','Polo celeste',colors['success']),('axis','Eje de la montura',colors['danger'])]:
            point=overlay[key]
            if point is None:continue
            px,py=xy((point['x'],point['y']));inside=point['inside']
            if not inside:
                dx,dy=px-w/2,py-h/2
                scale=min((max(iw/2-18,1)/abs(dx)) if dx else 1e9,(max(ih/2-18,1)/abs(dy)) if dy else 1e9)
                px,py=w/2+dx*scale,h/2+dy*scale
                c.create_line(px-dx*min(scale,.04),py-dy*min(scale,.04),px,py,fill=color,arrow='last',width=2)
                label+=' · fuera'
            locations[key]=(px,py)
            if key=='axis':c.create_oval(px-10,py-10,px+10,py+10,outline=color,width=2)
            elif key=='pole':
                c.create_line(px-12,py,px+12,py,fill=color,width=2);c.create_line(px,py-12,px,py+12,fill=color,width=2)
            else:c.create_oval(px-4,py-4,px+4,py+4,outline=color,width=2)
            anchor='w' if px<w/2 else 'e';tx=px+15 if anchor=='w' else px-15
            c.create_text(tx,max(12,min(h-12,py-15)),text=label,fill=color,anchor=anchor,font=(self.app.font,8,'bold'))
        if 'pole' in locations and 'axis' in locations:
            c.create_line(*locations['axis'],*locations['pole'],fill=colors['success'],dash=(4,4),width=2)
        if overlay['pole'] is None:
            c.create_text(w/2,17,text='Polo fuera de este campo · usa las indicaciones de la base',fill=colors['accent'],font=(self.app.font,9))
