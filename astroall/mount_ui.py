"""Native hand controller for the shared INDI mount connection."""
import json
from datetime import datetime,timezone
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
from .geometry import parse_angle
from .mount_service import HandController,profile,serial_ports,save_profile

CHECKLIST=[
    'GoTo con límite y PARAR visible',
    'Mando: para al soltar (máx. 1.5 s)',
    'Volver a Home desde Apuntado',
    'Lee hora y sitio al conectar',
]

def _ra_hms(ra_hours):
    total=round((float(ra_hours)%24)*3600)
    return f'{total//3600:02d}h {total%3600//60:02d}m {total%60:02d}s'

def _dec_dms(dec_deg):
    dec=float(dec_deg);total=round(abs(dec)*3600)
    return f"{'−' if dec<0 else '+'}{total//3600:02d}° {total%3600//60:02d}′ {total%60:02d}″"

def _target_note(app):
    target=getattr(app,'selected_target',None)
    if target is None: return 'JNow · sin objetivo en plan'
    return 'Objetivo: '+str(getattr(target,'name',None) or target)

def _refresh_pills(app,connected,site_ok):
    pills=getattr(app,'mount_pills',None)
    if not pills: return
    c=app.colors
    if connected:
        pills['connect'].configure(text='●  MONTURA CONECTADA',fg=c['success'])
    else:
        pills['connect'].configure(text='○  MONTURA DESCONECTADA',fg=c['muted'])
    if site_ok:
        pills['site'].configure(text='●  HORA/SITIO LEÍDOS',fg=c['success'])
    else:
        pills['site'].configure(text='○  HORA/SITIO PENDIENTE',fg=c['muted'])
    if getattr(app,'night',False):
        pills['night'].configure(text='●  MODO NOCHE',fg=c['danger'])
    else:
        pills['night'].configure(text='○  MODO NOCHE',fg=c['muted'])

def _refresh_cards(app,coords,state,sample,tracking,site_ok):
    cards=getattr(app,'mount_cards',None)
    if not cards: return
    def set_card(key,value,note):
        pair=cards.get(key)
        if not pair: return
        value_widget,note_widget=pair
        if value_widget.winfo_exists(): value_widget.configure(text=value)
        if note_widget.winfo_exists(): note_widget.configure(text=note)
    if coords:
        try: set_card('ra',_ra_hms(coords['RA']),'Siguiendo · velocidad sideral' if tracking else 'Seguimiento parado')
        except (TypeError,ValueError,KeyError): set_card('ra','—','Sin coordenadas')
        try: set_card('dec',_dec_dms(coords['DEC']),_target_note(app))
        except (TypeError,ValueError,KeyError): set_card('dec','—','Sin coordenadas')
    else:
        set_card('ra','—','Sin coordenadas');set_card('dec','—','Sin coordenadas')
    if sample and sample.get('UTC'):
        try:
            from .timekeeping import clock_snapshot,load_settings
            settings=load_settings();clock=clock_snapshot(settings)
            tz=settings.get('timezone','America/Mexico_City')
            place='Oaxaca' if 'Mexico_City' in tz else tz.split('/')[-1].replace('_',' ')
            local=clock['local'][11:16]
        except Exception:
            local=sample['UTC'][11:16];place='UTC'
        try: note=f"{float(sample['LAT']):.3f}° N · {abs(float(sample['LON'])):.3f}° O · de la montura"
        except (TypeError,ValueError,KeyError): note='De la montura'
        set_card('site',local+' · '+place,note)
    else:
        set_card('site','—','Sin lectura · usa Sincronizar GPS')
    if state is None:
        set_card('state','DESCONECTADA','Selecciona el puerto y pulsa Conectar')
    else:
        raw=state.get('STATE','Idle')
        label={'Idle':'SIGUIENDO' if tracking else 'EN POSICIÓN','SlewToTarget':'EN MOVIMIENTO',
               'FreeSlew':'EN MOVIMIENTO','ManualSlew':'EN MOVIMIENTO','Parking':'APARCANDO',
               'Homing':'BUSCANDO HOME','Parked':'EN PARK'}.get(raw,raw)
        set_card('state',label,'Sin errores · puerto estable')

def _data_card(app,parent,title):
    outer=app.frame(parent,'card',highlightbackground=app.colors['border'],highlightthickness=1)
    inside=app.frame(outer,'card');inside.pack(fill='both',expand=True,padx=12,pady=3)
    app.label(inside,title,size=8,color='muted',bold=True).pack(anchor='w')
    value=app.label(inside,'—',size=12,bold=True);value.pack(anchor='w',pady=(2,0))
    note=app.label(inside,'',size=8,color='muted');note.pack(anchor='w',pady=(2,0))
    return outer,value,note

def mount_page(app):
    from .ui_widgets import RoundedButton
    if not hasattr(app,'hand'):
        app.mount_snapshot={};app.mount_fields={k:tk.StringVar(value=v) for k,v in profile().items()}
        app.mount_status=tk.StringVar(value='Desconectada · no se abre el Arduino al iniciar')
        app.hand=HandController(app.post,lambda s:update(app,s),app.write)
    cfg=app.mount_fields
    pills=app.frame(app.content,'bg');pills.pack(fill='x',pady=(0,6))
    app.label(pills,'●',color='accent',size=10).pack(side='left')
    app.label(pills,'● ●',color='muted',size=10).pack(side='left',padx=(2,6))
    app.label(pills,'Astro One4All',size=12,bold=True).pack(side='left')
    pillbox=app.frame(pills,'bg');pillbox.pack(side='right')
    app.mount_pills={}
    for key in ('connect','site','night'):
        pill=tk.Label(pillbox,text='',bg=app.colors['field'],fg=app.colors['muted'],
                      font=(app.font,8,'bold'),padx=10,pady=3)
        pill.pack(side='left',padx=(6,0));app.mount_pills[key]=pill
    top,body=app.card(app.content,'',None)
    top.pack(fill='x')
    row=app.frame(body,'card');row.pack(fill='x')
    ports=serial_ports()
    port_widget=None
    if len(ports)==1 and not cfg['port'].get(): cfg['port'].set(ports[0])
    for label,key,choices,width in [('Perfil','driver',['indi_astroall_oat','indi_simulator_telescope','indi_lx200_OpenAstroTech'],25),('Puerto USB','port',ports,26),('Baudios','baud',['19200','9600','38400','57600','115200'],9)]:
        col=app.frame(row,'card');col.pack(side='left',fill='x',expand=True,padx=(0,10))
        app.label(col,label,size=8,color='muted').pack(anchor='w')
        widget=ttk.Combobox(col,textvariable=cfg[key],values=choices,width=width);widget.pack(fill='x',pady=5)
        if key=='port': port_widget=widget
    buttons=app.frame(body,'card');buttons.pack(fill='x',pady=(8,0))
    def connect():
        value={k:v.get().strip() for k,v in cfg.items()}
        if value['driver']=='indi_simulator_telescope': value['device']='Telescope Simulator'
        app.hand.submit('connect',value)
        app.write('Conectando… La consulta de producto y versión ocurre en el mismo controlador que maneja el puerto.')
    def refresh():
        found=serial_ports();port_widget.configure(values=found)
        if len(found)==1 and cfg['port'].get() not in found: cfg['port'].set(found[0])
        app.write('Puertos detectados: '+(', '.join(found) or 'ninguno; comprueba el cable USB y la alimentación del Mega.'))
    def home():
        if messagebox.askyesno('Volver a Home','¿Mover a la referencia Home que ya tiene el OAT? Comprueba que el recorrido esté libre.',parent=app.root): app.hand.submit('home')
    def diagnostic():
        path=Path.home()/'.local/state/astroall/mount-diagnostic.json'
        try: data=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):
            app.write('Sin diagnóstico de montura todavía: conecta primero la montura para probar la comunicación.')
            return
        firmware=data.get('firmware',{}) or {};transcript=data.get('transcript',[]) or []
        product=firmware.get('PRODUCT','?');version=firmware.get('VERSION','?')
        app.write(f"Comunicación OAT: {product} {version} · etapa {data.get('stage','?')} · {len(transcript)} comandos registrados en el diagnóstico.")
        app.mount_status.set(f'Comunicación: {product} {version} · {len(transcript)} comandos en el registro')
    app.button(buttons,'Conectar',connect,primary=True).pack(side='left')
    app.button(buttons,'Desconectar',lambda:app.hand.submit('disconnect')).pack(side='left',padx=8)
    app.button(buttons,'Buscar puertos',refresh).pack(side='left')
    app.button(buttons,'Home',home).pack(side='left',padx=6)
    app.button(buttons,'PARAR',lambda:app.hand.submit('abort'),danger=True).pack(side='right')
    app.label(body,variable=app.mount_status,size=9,color='accent',anchor='w',wraplength=740,justify='left').pack(fill='x',pady=(8,0))
    main=app.frame(app.content,'bg');main.pack(fill='x',pady=(6,0))
    left=app.frame(main,'bg',width=300);left.pack(side='left',fill='y');left.pack_propagate(False)
    app.label(left,'Montura',size=15,bold=True).pack(anchor='w')
    app.label(left,'El corazón del sistema: control completo de tu OAT con el estado siempre visible.',
              size=10,color='muted',wraplength=290,justify='left').pack(anchor='w',pady=(6,12))
    for item in CHECKLIST:
        item_row=app.frame(left,'bg');item_row.pack(fill='x',pady=(0,6))
        app.label(item_row,'✓',size=10,color='success',bold=True).pack(side='left',anchor='n')
        app.label(item_row,item,size=10,wraplength=268,justify='left').pack(side='left',padx=(6,0))
    right=app.frame(main,'bg');right.pack(side='left',fill='both',expand=True,padx=(16,0))
    grid=app.frame(right,'bg');grid.pack(fill='x')
    grid.columnconfigure(0,weight=1);grid.columnconfigure(1,weight=1)
    app.mount_cards={}
    for (key,title),(r,c) in zip((('ra','ASCENSIÓN RECTA'),('dec','DECLINACIÓN'),
                                 ('site','HORA / SITIO LEÍDOS'),('state','ESTADO')),
                                ((0,0),(0,1),(1,0),(1,1))):
        outer,value,note=_data_card(app,grid,title)
        outer.grid(row=r,column=c,sticky='nsew',padx=(0,8) if c==0 else (0,0),pady=(0,4) if r==0 else (0,0))
        app.mount_cards[key]=(value,note)
    padrow=app.frame(right,'bg');padrow.pack(fill='x',pady=(10,0))
    pad=app.frame(padrow,'bg');pad.pack(side='left')
    for label,direction,r,c in [('N','n',0,1),('O','w',1,0),('E','e',1,2),('S','s',2,1)]:
        b=RoundedButton(pad,label,None,app,width=64)
        b.grid(row=r,column=c,padx=3,pady=3)
        b.bind('<ButtonPress-1>',lambda event,d=direction:app.hand.hold(d),add='+')
        b.bind('<ButtonRelease-1>',lambda event:app.hand.release(),add='+')
        b.bind('<Leave>',lambda event:app.hand.release(),add='+')
        b.bind('<Destroy>',lambda event:app.hand.release(),add='+')
    stop=RoundedButton(pad,'PARAR',lambda:app.hand.submit('abort'),app,danger=True,width=64)
    stop.grid(row=1,column=1,padx=3,pady=3)
    if not getattr(app,'mount_focus_bound',False):
        app.root.bind('<FocusOut>',lambda event:app.hand.release(),add='+');app.mount_focus_bound=True
    side=app.frame(padrow,'bg');side.pack(side='left',fill='y',padx=(16,0))
    if not hasattr(app,'mount_rate'): app.mount_rate=tk.StringVar(value='1 · Fino')
    rate=ttk.Combobox(side,textvariable=app.mount_rate,values=['1 · Fino','2 · Centrar','3 · Buscar','4 · Rápido'],state='readonly',width=14)
    rate.pack(pady=(2,6));rate.bind('<<ComboboxSelected>>',lambda e:app.hand.submit('rate',rate.current()))
    app.button(side,'Seguir',lambda:app.hand.submit('track',True)).pack(fill='x',pady=2)
    app.button(side,'Parar seguimiento',lambda:app.hand.submit('track',False)).pack(fill='x',pady=2)
    app.label(right,'Sideral según calibración del firmware · posición calculada, sin encoders.',
              size=8,color='muted',justify='left',wraplength=600).pack(fill='x',pady=(4,0))
    actions=app.frame(right,'bg');actions.pack(fill='x',pady=(6,0))
    app.button(actions,'Sincronizar GPS',lambda:app.hand.submit('gps_sync'),primary=True).pack(side='left')
    app.button(actions,'Volver a Home',home).pack(side='left',padx=6)
    app.button(actions,'Probar comunicación',diagnostic).pack(side='left')
    outer,goto=app.card(app.content,'','APUNTADO')
    outer.pack(fill='x',pady=(6,0))
    if not hasattr(app,'mount_ra'): app.mount_ra=tk.StringVar();app.mount_dec=tk.StringVar()
    entries=app.frame(goto,'card');entries.pack(fill='x')
    for label,var in [('AR JNow · hh:mm:ss',app.mount_ra),('DEC JNow · ±gg:mm:ss',app.mount_dec)]:
        col=app.frame(entries,'card');col.pack(side='left',fill='x',expand=True,padx=(0,10))
        app.label(col,label,size=9,color='muted').pack(anchor='w',pady=(0,4))
        ttk.Entry(col,textvariable=var,width=22).pack(fill='x')
    def manual_goto():
        try:
            ra=parse_angle(app.mount_ra.get(),True)/15;dec=parse_angle(app.mount_dec.get())
            if messagebox.askyesno('Mover la montura','¿Mover a estas coordenadas de fecha? Confirma Home, hora, ubicación y espacio libre en el OAT.',parent=app.root): app.hand.submit('goto',ra,dec)
        except ValueError as exc: app.write(str(exc))
    gotorow=app.frame(goto,'card');gotorow.pack(fill='x',pady=(10,0))
    app.button(gotorow,'Ir a estas coordenadas',manual_goto,primary=True).pack(side='left')
    app.button(gotorow,'Volver a Home existente',home).pack(side='left',padx=6)
    app.button(gotorow,'Salir de Park',lambda:app.hand.submit('park',False)).pack(side='left',padx=6)
    app.label(goto,'No redefine Home ni busca sensores · el LCD conserva su uso autónomo.',size=8,color='muted',justify='left',wraplength=800).pack(anchor='w',pady=(8,0))
    update(app,app.mount_snapshot)

def update(app,snapshot):
    app.mount_snapshot=snapshot
    app.mount_observed_utc=datetime.now(timezone.utc).isoformat()
    def values(name): return next((v['values'] for k,v in snapshot.items() if k.endswith('/'+name)),{})
    def prop(name): return next((p for k,p in snapshot.items() if k.endswith('/'+name)),{})
    connection=values('CONNECTION');connection_prop=prop('CONNECTION')
    connected=connection.get('CONNECT')=='On' and connection_prop.get('state')!='Alert'
    sample=values('OAT_SITE_TIME');sample_prop=prop('OAT_SITE_TIME')
    site_ok=bool(sample.get('UTC')) and sample_prop.get('state')=='Ok'
    if not connected:
        app.mount_status.set('Desconectada · selecciona el puerto y pulsa Conectar')
        app.mount_badge.set('Montura: desconectada')
        _refresh_pills(app,False,False)
        _refresh_cards(app,None,None,None,False,False)
        return
    app.mount_badge.set('Montura: conectada')
    if sample.get('UTC') and sample_prop.get('state')=='Ok' and getattr(app,'mount_time_sample',None)!=sample.get('MONOTONIC'):
        app.mount_time_sample=sample['MONOTONIC']
        from .timekeeping import import_mount_time
        try:
            imported=import_mount_time(sample)
            if imported.get('use_mount_time',True):
                if sample.get('GPS_SYNC')=='1':
                    app.write('Hora UTC y ubicación sincronizadas desde el GPS del OAT (:gT#).')
                else:
                    app.write('Hora UTC y ubicación importadas de OAT. La confirmación GPS se consulta en el LCD.')
                if app.current_page=='atlas':
                    from .atlas_ui import refresh_visibility,refresh_details
                    refresh_visibility(app);refresh_details(app)
        except Exception as exc: app.write('No se usó la hora/ubicación OAT: '+str(exc))
    coords=values('EQUATORIAL_EOD_COORD');firmware=values('FIRMWARE_INFO');state=values('OAT_STATUS')
    tracking=values('TELESCOPE_TRACK_STATE').get('TRACK_ON')=='On'
    device=next(iter(snapshot),'Montura').split('/')[0];app.mount_fields['device'].set(device)
    app.mount_status.set(f"{device} · {firmware.get('VERSION','versión del controlador')} · {state.get('STATE','conectada')}")
    _refresh_pills(app,True,site_ok)
    _refresh_cards(app,coords,state,sample,tracking,site_ok)
