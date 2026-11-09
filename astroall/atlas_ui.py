"""Offline atlas, camera framing, favorites and sampled night visibility."""
from dataclasses import asdict
from datetime import datetime
import json
import math
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from .catalog import Catalog,Target,TYPES,save_target,saved_targets
from .geometry import project,offset,mosaic,format_ra,format_dec,parse_angle
from .optics import field_width
from .sky import Site,visibility,night_tracks,eod_position,atlas_visibility
from .solve import Position
from .timekeeping import load_settings,save_settings
from .recommendations import SENSORS,recommend,describe,capture_proposal

def site_window(app):
    saved=load_settings();dialog=tk.Toplevel(app.root);dialog.title('Astro One4All · Ubicación y tiempo');dialog.configure(bg=app.colors['bg'])
    body=ttk.Frame(dialog,padding=22);body.pack(fill='both',expand=True)
    fields={}
    for key,label,default in [('latitude','Latitud · norte positivo',''),('longitude','Longitud · oeste negativo',''),('elevation','Altitud sobre el mar / m',0),('timezone','Zona horaria','America/Mexico_City')]:
        fields[key]=tk.StringVar(value=saved.get(key) if saved.get(key) is not None else default)
        ttk.Label(body,text=label).pack(anchor='w',pady=(7,3));ttk.Entry(body,textvariable=fields[key],width=36).pack(fill='x')
    confirmed=tk.BooleanVar(value=saved.get('clock_confirmed',False))
    from .timekeeping import clock_snapshot,write_settings
    clock=clock_snapshot(saved)
    ttk.Label(body,text=f"{clock['source']}\nUTC: {clock['utc'][:19]} · local: {clock['local'][:19]}\nOAT debe confirmar el GPS en su LCD antes de conectar.",justify='left').pack(anchor='w',pady=12)
    mount_clock=tk.BooleanVar(value=saved.get('use_mount_time',True))
    ttk.Checkbutton(body,text='Leer hora y ubicación OAT al conectar',variable=mount_clock).pack(anchor='w')
    ttk.Checkbutton(body,text='He comprobado fecha y hora del PC',variable=confirmed).pack(anchor='w')
    def save():
        try:
            site=Site(float(fields['latitude'].get()),float(fields['longitude'].get()),float(fields['elevation'].get()),fields['timezone'].get().strip())
            if mount_clock.get() and saved.get('clock_anchor'):
                if saved.get('latitude')!=site.latitude or saved.get('longitude')!=site.longitude:
                    saved['clock_source']='Hora OAT; ubicación introducida manualmente'
                saved.update(timezone=site.zone,latitude=site.latitude,longitude=site.longitude,elevation=site.elevation,use_mount_time=True);write_settings(saved)
            else:
                value=save_settings(site.zone,site.longitude,confirmed.get(),site.latitude,site.elevation)
                value['use_mount_time']=mount_clock.get();write_settings(value)
            app.write('Ubicación y zona horaria guardadas entre sesiones.');dialog.destroy()
            if app.current_page=='atlas': refresh_visibility(app)
            elif app.current_page=='polar':app.show('polar')
        except Exception as exc: messagebox.showerror('Revisa la ubicación',str(exc),parent=dialog)
    ttk.Button(body,text='Guardar ubicación y tiempo',command=save).pack(fill='x',pady=(16,0))

def atlas_page(app):
    if not hasattr(app,'atlas'):
        from .preferences import load
        settings=load()
        app.atlas={'catalog':Catalog(),'query':tk.StringVar(),'kind':tk.StringVar(value='Todos'),'favorite':tk.BooleanVar(),
                   'focal':tk.StringVar(value='50'),'sensor_w':tk.StringVar(value='22.3'),'sensor_h':tk.StringVar(value='14.9'),
                   'angle':tk.StringVar(value='0'),'rows':tk.StringVar(value='1'),'columns':tk.StringVar(value='1'),'overlap':tk.StringVar(value='20'),
                   'detail':tk.StringVar(value='Selecciona un objeto para explorar su campo.'),'selected':None,'zoom':1.6,'targets':[],'night':None}
        app.atlas.update(sensor=tk.StringVar(value=settings['sensor']),guided=tk.BooleanVar(value=False),proposal=tk.StringVar(),sky_generation=0,sky_running=False)
        app.atlas['focal'].set(str(settings['focal']))
        def changed(*args):
            if app.current_page!='atlas':return
            token=app.atlas.get('focal_timer')
            if token:
                try:app.root.after_cancel(token)
                except tk.TclError:pass
            app.atlas['focal_timer']=app.root.after(200,lambda:update_proposal(app))
        app.atlas['focal'].trace_add('write',changed)
    a=app.atlas
    bar=app.frame(app.content);bar.pack(fill='x',pady=(0,12))
    search=ttk.Entry(bar,textvariable=a['query'],width=23);search.pack(side='left',fill='x',expand=True)
    search.bind('<Return>',lambda e:search_targets(app))
    app.button(bar,'Buscar',lambda:search_targets(app),primary=True).pack(side='left',padx=6)
    kinds=['Todos','Messier']+sorted(set(TYPES.values()))
    kind=ttk.Combobox(bar,textvariable=a['kind'],values=kinds,state='readonly',width=19);kind.pack(side='left',padx=6)
    kind.bind('<<ComboboxSelected>>',lambda e:search_targets(app))
    ttk.Checkbutton(bar,text='Favoritos',variable=a['favorite'],command=lambda:search_targets(app)).pack(side='left',padx=6)
    app.button(bar,'Ubicación',lambda:site_window(app)).pack(side='right')
    split=app.frame(app.content);split.pack(fill='both',expand=True)
    left=app.frame(split);left.pack(side='left',fill='y',padx=(0,12))
    tree=ttk.Treeview(left,columns=('visible',),show='tree headings',height=12,selectmode='browse')
    tree.heading('#0',text='Objeto / nombre');tree.column('#0',width=175,minwidth=125)
    tree.heading('visible',text='Visibilidad ahora');tree.column('visible',width=210,stretch=False)
    tree.tag_configure('hidden',foreground=app.colors['muted']);tree.tag_configure('low',foreground=app.colors['danger']);tree.tag_configure('visible',foreground=app.colors['success'])
    tree.pack(side='left',fill='both',expand=True)
    scroll=ttk.Scrollbar(left,orient='vertical',command=tree.yview);scroll.pack(side='right',fill='y');tree.configure(yscrollcommand=scroll.set)
    a['tree']=tree;tree.bind('<<TreeviewSelect>>',lambda e:select_target(app))
    right=app.frame(split);right.pack(side='left',fill='both',expand=True)
    canvas=tk.Canvas(right,bg=app.colors['preview'],height=238,highlightthickness=1,highlightbackground=app.colors['border'])
    canvas.pack(fill='both',expand=True);a['canvas']=canvas
    canvas.bind('<Configure>',lambda e:draw_chart(app))
    canvas.bind('<MouseWheel>',lambda e:zoom(app,.8 if e.delta>0 else 1.25))
    canvas.bind('<Button-4>',lambda e:zoom(app,.8));canvas.bind('<Button-5>',lambda e:zoom(app,1.25))
    canvas.bind('<Double-Button-1>',lambda e:chart_pick(app,e.x,e.y))
    controls=app.frame(right);controls.pack(fill='x',pady=6)
    for text,factor in [('+',.8),('−',1.25)]: app.button(controls,text,lambda f=factor:zoom(app,f)).pack(side='left',padx=2)
    app.button(controls,'★ Guardar',lambda:favorite(app)).pack(side='left',padx=4)
    app.button(controls,'Agregar al programa',lambda:to_plan(app)).pack(side='right')
    app.button(controls,'GoTo',lambda:goto_selected(app)).pack(side='right',padx=4)
    app.label(right,variable=a['detail'],size=9,justify='left',anchor='w',wraplength=560).pack(fill='x',pady=(2,5))
    outer,framing=app.card(app.content,'Encuadre y propuesta de captura','REVISA LA PROPUESTA ANTES DE INICIAR')
    outer.pack(fill='x',pady=(12,0))
    row=app.frame(framing,'card');row.pack(fill='x')
    sensor=ttk.Combobox(row,textvariable=a['sensor'],values=list(SENSORS),state='readonly',width=12);sensor.pack(side='left',padx=(0,10))
    sensor.bind('<<ComboboxSelected>>',lambda e:update_proposal(app))
    for key,label,width,values in [('focal','Usaré / mm',7,['10','18','35','45','50','55','100','135','200','250']),('angle','Rotación / °',6,None),('rows','Filas',4,['1','2','3','4','5']),('columns','Columnas',4,['1','2','3','4','5']),('overlap','Solape / %',5,None)]:
        col=app.frame(row,'card');col.pack(side='left',padx=(0,10))
        app.label(col,label,size=8,color='muted').pack(anchor='w')
        widget=ttk.Combobox(col,textvariable=a[key],values=values,width=width) if values else ttk.Entry(col,textvariable=a[key],width=width)
        widget.pack(pady=4);widget.bind('<Return>',lambda e:draw_chart(app));widget.bind('<<ComboboxSelected>>',lambda e:draw_chart(app))
    app.button(row,'Usar recomendada',lambda:update_proposal(app,apply_focal=True)).pack(side='left',padx=4,pady=(12,0))
    app.button(row,'Plan de esta noche',lambda:plan_night(app)).pack(side='right',pady=(12,0))
    bottom=app.frame(framing,'card');bottom.pack(fill='x',pady=(4,0))
    ttk.Checkbutton(bottom,text='Guiado PHD2 validado',variable=a['guided'],command=lambda:update_proposal(app)).pack(side='left')
    app.button(bottom,'Coordenadas propias',lambda:custom_target(app)).pack(side='right')
    app.label(framing,variable=a['proposal'],size=8,color='accent',wraplength=980,justify='left',anchor='w').pack(fill='x',pady=(5,0))
    search_targets(app)
    schedule_visibility(app)

def schedule_visibility(app):
    token=app.atlas.get('timer')
    if token:
        try: app.root.after_cancel(token)
        except tk.TclError: pass
    def tick():
        if app.current_page=='atlas': refresh_visibility(app);schedule_visibility(app)
    app.atlas['timer']=app.root.after(60000,tick)

def search_targets(app):
    a=app.atlas
    try:
        kind=next((k for k,v in TYPES.items() if v==a['kind'].get()),'')
        if a['favorite'].get():
            from .catalog import normalized
            targets=[t for t in saved_targets() if all(word in normalized(t.label+' '+t.aliases) for word in normalized(a['query'].get()).split())]
        else: targets=a['catalog'].search(a['query'].get(),kind,150,a['kind'].get()=='Messier')
        a['targets']=targets;tree=a['tree'];tree.delete(*tree.get_children())
        for index,target in enumerate(targets):
            label=(f'M{target.messier}' if target.messier else target.identifier)+(' · '+target.name if target.name!=target.identifier else '')
            tree.insert('','end',iid=str(index),text=label,values=('Comprobando…',))
        if targets:
            selected=next((i for i,t in enumerate(targets) if a['selected'] and t.identifier==a['selected'].identifier),0)
            tree.selection_set(str(selected));tree.see(str(selected));select_target(app)
        else: a['detail'].set('No se encontraron objetos. Prueba M31, Orión, NGC 7000 o Vía Láctea.')
    except Exception as exc: app.write(str(exc))

def select_target(app):
    a=app.atlas;selection=a['tree'].selection()
    if not selection: return
    target=a['targets'][int(selection[0])];changed=a['selected'] is None or a['selected'].identifier!=target.identifier
    a['selected']=target;a['night']=None
    update_proposal(app,apply_focal=changed);refresh_visibility(app)

def update_proposal(app,apply_focal=False):
    a=app.atlas;t=a['selected']
    if not t: return
    proposal=recommend(t,a['sensor'].get(),a['guided'].get());a['recommendation']=proposal
    a['sensor_w'].set(str(proposal['sensor_w']));a['sensor_h'].set(str(proposal['sensor_h']))
    if apply_focal: a['focal'].set(str(proposal['focal']))
    other=recommend(t,'Full Frame' if a['sensor'].get()!='Full Frame' else 'APS-C Canon',a['guided'].get())
    from .preferences import load
    try:
        used=capture_proposal(t,a['sensor'].get(),a['focal'].get(),a['guided'].get(),load());a['used_proposal']=used
        a['proposal'].set(f"Recomendada: {proposal['focal']} mm ({proposal['sensor']}) · {other['focal']} mm ({other['sensor']}). Puedes cambiar «Usaré / mm»."
                         +f"\nUsarás {used['focal']:g} mm · {used['count']} fotos × {used['exposure']} s · ISO {used['iso']} · {used['minutes']} min de integración."
                         +'\nAjusta el lente físicamente y comprueba enfoque e histograma con una foto de prueba.')
    except ValueError as exc:a['proposal'].set(str(exc));return
    draw_chart(app)

def refresh_details(app):
    refresh_visibility(app)

def refresh_visibility(app):
    a=app.atlas;t=a['selected']
    if not t: return
    a['sky_generation']+=1;generation=a['sky_generation']
    text=f'{t.label}\nJ2000   AR {format_ra(t.ra_deg)}   DEC {format_dec(t.dec_deg)}'
    if t.major_arcmin: text+=f'   · {t.major_arcmin:.1f}′'
    a['detail'].set(text+'\nConfigura ubicación y reloj para altura, Luna y hora sidérea.')
    try: site=Site.from_settings(load_settings())
    except ValueError as exc:
        for item in a['tree'].get_children(): a['tree'].set(item,'visible','Falta hora/ubicación')
        a['detail'].set(text+'\n'+str(exc));return
    if a['sky_running']: return
    a['sky_running']=True;targets=list(a['targets'])
    def show(rows,value,error=None):
        a['sky_running']=False
        if app.current_page!='atlas': return
        if generation!=a['sky_generation']: refresh_visibility(app);return
        if error: a['detail'].set(text+'\n'+error);return
        for i,row in enumerate(rows):
            item=str(i)
            if a['tree'].exists(item):
                tag='hidden' if row['alt_deg']<0 else 'low' if row['alt_deg']<20 else 'visible'
                a['tree'].item(item,values=(row['label'],),tags=(tag,))
        a['detail'].set(text+f"\n{value['visibility_label']} · Alt {value['alt_deg']:.1f}° · Luna a {value['moon_separation_deg']:.0f}°"
                        +f"\nTSL {format_ra(value['sidereal_hours']*15)} · HA objeto {value['ha_hours']:+.2f} h · "+('Noche astronómica' if value['astronomical_darkness'] else 'Cielo aún iluminado por el Sol'))
    def work():
        try:
            from .sky import utc_instant
            instant=utc_instant();rows=atlas_visibility(targets,site,instant);value=visibility(t,site,instant)
            app.post(lambda:show(rows,value))
        except Exception as exc:
            error=str(exc);app.post(lambda:show([],None,error))
    threading.Thread(target=work,daemon=True).start()

def field(app):
    a=app.atlas;focal=float(a['focal'].get())
    return field_width(float(a['sensor_w'].get()),focal),field_width(float(a['sensor_h'].get()),focal)

def panels(app):
    a=app.atlas;t=a['selected']
    if not t: raise ValueError('Selecciona un objetivo.')
    w,h=field(app)
    return mosaic(t,w,h,int(a['rows'].get()),int(a['columns'].get()),float(a['overlap'].get())/100,float(a['angle'].get()))

def zoom(app,factor):
    app.atlas['zoom']=min(12,max(.4,app.atlas['zoom']*factor));draw_chart(app)

def draw_chart(app):
    a=app.atlas;c=a.get('canvas');t=a['selected']
    if not c or not c.winfo_exists() or not t: return
    c.configure(bg=app.colors['preview'],highlightbackground=app.colors['border']);c.delete('all')
    w,h=max(100,c.winfo_width()),max(100,c.winfo_height())
    try:
        fw,fh=field(app);m=panels(app)
        span=min(155,max(fw*int(a['columns'].get()),fh*int(a['rows'].get()))*a['zoom'])
        scale=min(w,h)/(2*math.tan(math.radians(min(160,span)/2)))
        def pixel(position):
            v=project(position,t)
            return None if v is None else (w/2-v[0]*scale,h/2-v[1]*scale)
        for star in a['catalog'].region(t.ra_deg,t.dec_deg,min(179,span),stars=True,limit=2500):
            xy=pixel(Position(star['ra_deg'],star['dec_deg']))
            if not xy or not (0<=xy[0]<=w and 0<=xy[1]<=h): continue
            x,y=xy;r=max(.6,2.6-star['magnitude']*.3)
            c.create_oval(x-r,y-r,x+r,y+r,fill=app.colors['text'],outline='')
        picks=[]
        for obj in a['catalog'].region(t.ra_deg,t.dec_deg,min(179,span),limit=140):
            p=Position(obj['ra_deg'],obj['dec_deg']);xy=pixel(p)
            if not xy or not (5<xy[0]<w-5 and 5<xy[1]<h-5): continue
            x,y=xy;r=max(3,min(22,math.radians((obj['major_arcmin'] or 4)/60)*scale/2))
            c.create_oval(x-r,y-r*.65,x+r,y+r*.65,outline=app.colors['muted'],width=1)
            if obj['messier'] or obj['identifier']==t.identifier:
                c.create_text(x+6,y-8,text=f"M{obj['messier']}" if obj['messier'] else obj['identifier'],anchor='sw',fill=app.colors['muted'],font=(app.font,8))
            picks.append((x,y,obj['identifier']))
        a['picks']=picks;angle=math.radians(float(a['angle'].get()))
        for panel in m:
            center=Position(panel['ra_deg'],panel['dec_deg']);points=[]
            for x,y in [(-fw/2,-fh/2),(fw/2,-fh/2),(fw/2,fh/2),(-fw/2,fh/2)]:
                pos=offset(center,x*math.cos(angle)+y*math.sin(angle),-x*math.sin(angle)+y*math.cos(angle));xy=pixel(pos)
                if xy: points.extend(xy)
            if len(points)==8: c.create_polygon(*points,outline=app.colors['accent'],fill='',width=2)
            xy=pixel(center)
            if xy: c.create_text(*xy,text=str(panel['panel']),fill=app.colors['accent'],font=(app.font,9,'bold'))
        c.create_line(w/2-7,h/2,w/2+7,h/2,fill=app.colors['success']);c.create_line(w/2,h/2-7,w/2,h/2+7,fill=app.colors['success'])
        c.create_text(12,10,text=f'N ↑    E ←       {fw:.2f}° × {fh:.2f}°',anchor='nw',fill=app.colors['accent'],font=(app.font,9))
        c.create_text(12,h-10,text='OpenNGC + HYG · J2000 · doble clic: seleccionar objeto',anchor='sw',fill=app.colors['muted'],font=(app.font,8))
        app.width.set(str(fw))
    except Exception as exc: c.create_text(w/2,h/2,text=str(exc),width=w-40,fill=app.colors['danger'])

def chart_pick(app,x,y):
    a=app.atlas
    nearest=sorted(a.get('picks',[]),key=lambda p:(x-p[0])**2+(y-p[1])**2)
    if nearest and math.hypot(x-nearest[0][0],y-nearest[0][1])<24:
        a['query'].set(nearest[0][2]);a['favorite'].set(False);a['kind'].set('Todos');search_targets(app)

def favorite(app):
    if app.atlas['selected']: save_target(app.atlas['selected']);app.write('Objetivo guardado en Favoritos.')

def to_plan(app):
    try:
        selected=app.atlas['selected'];items=panels(app);app.plan_targets=[]
        for panel in items:
            target=Target(f"{selected.identifier}_P{panel['panel']}",selected.name+f" · panel {panel['panel']}",panel['ra_deg'],panel['dec_deg'],source='Mosaico calculado sobre '+selected.source)
            app.plan_targets.append(target)
        app.selected_target=app.plan_targets[0]
        from .preferences import load
        settings=load()
        focal=float(app.atlas['focal'].get())
        proposal=capture_proposal(selected,app.atlas['sensor'].get(),focal,app.atlas['guided'].get(),settings)
        app.show('session')
        from .session import Block
        from .session_ui import refresh_blocks
        s=app.sequence;s['blocks']=[Block(proposal['count'],proposal['exposure'],proposal['iso'],'Light',proposal['delay'])]
        for key in ('count','exposure','iso','delay'): s[key].set(str(proposal[key]))
        s['type'].set('Light');s['guide'].set(proposal['guided']);s['dither'].set('0');s['goto'].set(True)
        s['jpg_correct'].set(settings['jpg_correction'] or len(items)>1);s['recenter'].set(str(settings['jpg_every']))
        s['field_deg'].set(str(proposal['field_w']));s['framing']={'sensor':proposal['sensor'],'focal':focal,'width_deg':proposal['field_w']}
        refresh_blocks(app)
        s['recommendation'].set(f"{proposal['sensor']} · focal física {focal:g} mm · {proposal['minutes']} min por encuadre. Haz una foto de prueba y revisa enfoque e histograma.")
        app.write(f'{len(items)} encuadre(s) y propuesta de captura añadidos. Revisa focal física, enfoque, Home y límites antes de iniciar.')
    except Exception as exc: app.write(str(exc))

def goto_selected(app):
    target=app.atlas['selected']
    if not target: return
    try: site=Site.from_settings(load_settings())
    except Exception as exc: app.write(str(exc));return
    def prepare():
        view=visibility(target,site)
        if view['alt_deg']<10: raise ValueError(f"No se moverá: objetivo a {view['alt_deg']:.1f}° de altura; mínimo 10°.")
        return view
    def move(view):
        if messagebox.askyesno('GoTo desde el atlas',f"¿Apuntar a {target.label}?\nAltura: {view['alt_deg']:.1f}°. Confirma la referencia Home y los límites en tu montura.",parent=app.root):
            if not hasattr(app,'hand'): from .mount_ui import mount_page;app.show('mount')
            app.hand.submit('goto',view['ra_hours_eod'],view['dec_deg_eod'])
    app.task('Comprobando altura y coordenadas de fecha…',prepare,move)

def plan_night(app):
    try:
        site=Site.from_settings(load_settings());targets=app.atlas['targets'][:110]
        if not targets: raise ValueError('Busca primero objetos en el catálogo.')
    except Exception as exc: app.write(str(exc));return
    def show(result):
        app.atlas['night']=result;dialog=tk.Toplevel(app.root);dialog.title('Astro One4All · Esta noche');dialog.geometry('850x560');dialog.configure(bg=app.colors['bg'])
        body=ttk.Frame(dialog,padding=18);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Cielo oscuro · altura ≥20° · Luna a ≥20° cuando está sobre el horizonte').pack(anchor='w')
        ttk.Label(body,text=f"{result['times_local'][0][:10]} · {result['timezone']} · intervalos aproximados de 30 min").pack(anchor='w',pady=(4,12))
        tree=ttk.Treeview(body,columns=('alt','time'),show='tree headings',height=9);tree.heading('#0',text='Objetivo');tree.column('#0',width=500);tree.heading('alt',text='Alt. máxima');tree.heading('time',text='Tiempo útil');tree.column('alt',width=95);tree.column('time',width=90)
        tree.pack(fill='x')
        rows=sorted(result['tracks'],key=lambda x:x['usable_minutes'],reverse=True)
        for i,row in enumerate(rows): tree.insert('','end',iid=str(i),text=row['label'],values=(f"{row['max_alt_deg']:.0f}°",f"{row['usable_minutes']/60:.1f} h"))
        plot=tk.Canvas(body,height=180,bg=app.colors['preview'],highlightthickness=0);plot.pack(fill='both',expand=True,pady=12)
        def graph(event=None):
            plot.delete('all');selection=tree.selection()
            if not selection: return
            row=rows[int(selection[0])];w=max(300,plot.winfo_width());h=max(100,plot.winfo_height());n=len(row['altitudes'])
            for alt in (0,20,40,60,80):
                y=h-25-alt/90*(h-40);plot.create_line(34,y,w-8,y,fill=app.colors['border']);plot.create_text(25,y,text=str(alt),anchor='e',fill=app.colors['muted'])
            coords=[]
            for i,alt in enumerate(row['altitudes']):
                x=35+i/(n-1)*(w-48);y=h-25-alt/90*(h-40);coords.extend((x,y))
                if row['usable'][i]: plot.create_line(x,h-24,x,h-19,fill=app.colors['success'],width=3)
                if i%8==0: plot.create_text(x,h-8,text=result['times_local'][i][11:16],fill=app.colors['muted'],font=(app.font,8))
            plot.create_line(*coords,fill=app.colors['accent'],width=2)
        tree.bind('<<TreeviewSelect>>',graph);plot.bind('<Configure>',graph)
        if rows: tree.selection_set('0')
        def choose():
            if tree.selection():
                key=rows[int(tree.selection()[0])]['identifier'];app.atlas['query'].set(key);app.atlas['favorite'].set(False);app.atlas['kind'].set('Todos');dialog.destroy();search_targets(app)
        ttk.Button(body,text='Explorar objeto seleccionado',command=choose).pack(anchor='e')
    app.task('Calculando ventanas de esta noche…',lambda:night_tracks(targets,site),show)

def custom_target(app):
    dialog=tk.Toplevel(app.root);dialog.title('Objetivo propio · J2000');body=ttk.Frame(dialog,padding=20);body.pack(fill='both',expand=True)
    fields={}
    for key,label in [('name','Nombre'),('ra','AR J2000 · hh:mm:ss'),('dec','DEC J2000 · ±gg:mm:ss')]:
        fields[key]=tk.StringVar();ttk.Label(body,text=label).pack(anchor='w',pady=4);ttk.Entry(body,textvariable=fields[key],width=34).pack(fill='x')
    def save():
        try:
            import uuid
            t=Target('USER_'+uuid.uuid4().hex[:12],fields['name'].get().strip(),parse_angle(fields['ra'].get(),True),parse_angle(fields['dec'].get()),source='Coordenadas introducidas por el usuario')
            save_target(t);app.atlas['favorite'].set(True);app.atlas['query'].set(t.name);dialog.destroy();search_targets(app)
        except Exception as exc: messagebox.showerror('Revisa el objetivo',str(exc),parent=dialog)
    ttk.Button(body,text='Guardar en favoritos',command=save).pack(fill='x',pady=(14,0))
