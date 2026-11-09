"""Native hand controller for the shared INDI mount connection."""
import tkinter as tk
from datetime import datetime,timezone
from tkinter import ttk,messagebox
from .geometry import parse_angle,format_ra,format_dec
from .mount_service import HandController,profile,serial_ports,save_profile

def mount_page(app):
    if not hasattr(app,'hand'):
        app.mount_snapshot={};app.mount_fields={k:tk.StringVar(value=v) for k,v in profile().items()}
        app.mount_status=tk.StringVar(value='Desconectada · no se abre el Arduino al iniciar')
        app.hand=HandController(app.post,lambda s:update(app,s),app.write)
    cfg=app.mount_fields
    top,body=app.card(app.content,'Conecta tu montura','CONTROL INDI COMPARTIDO')
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
    app.button(buttons,'Conectar',connect,primary=True).pack(side='left')
    app.button(buttons,'Desconectar',lambda:app.hand.submit('disconnect')).pack(side='left',padx=8)
    app.button(buttons,'Buscar puertos',refresh).pack(side='left')
    app.button(buttons,'Leer hora/ubicación',lambda:app.hand.submit('read_time')).pack(side='left',padx=6)
    app.button(buttons,'PARAR',lambda:app.hand.submit('abort'),danger=True).pack(side='right')
    app.label(body,variable=app.mount_status,size=9,color='accent',anchor='w',wraplength=740,justify='left').pack(fill='x',pady=(10,0))
    mid=app.frame(app.content);mid.pack(fill='both',expand=True,pady=(14,0))
    outer,hand=app.card(mid,'Mantén pulsado para mover','MANDO')
    outer.pack(side='left',fill='both',expand=True,padx=(0,14))
    pad=app.frame(hand,'card');pad.pack(pady=4)
    for label,direction,row,column in [('N','n',0,1),('O','w',1,0),('E','e',1,2),('S','s',2,1)]:
        b=ttk.Button(pad,text=label,width=7)
        b.grid(row=row,column=column,padx=4,pady=4)
        b.bind('<ButtonPress-1>',lambda event,d=direction:app.hand.hold(d))
        b.bind('<ButtonRelease-1>',lambda event:app.hand.release())
        b.bind('<Leave>',lambda event:app.hand.release())
        b.bind('<Destroy>',lambda event:app.hand.release())
    if not getattr(app,'mount_focus_bound',False):
        app.root.bind('<FocusOut>',lambda event:app.hand.release(),add='+');app.mount_focus_bound=True
    if not hasattr(app,'mount_rate'): app.mount_rate=tk.StringVar(value='1 · Fino')
    rate=ttk.Combobox(hand,textvariable=app.mount_rate,values=['1 · Fino','2 · Centrar','3 · Buscar','4 · Rápido'],state='readonly',width=19)
    rate.pack(pady=6);rate.bind('<<ComboboxSelected>>',lambda e:app.hand.submit('rate',rate.current()))
    tracking=app.frame(hand,'card');tracking.pack(pady=8)
    app.button(tracking,'Seguir',lambda:app.hand.submit('track',True)).pack(side='left',padx=3)
    app.button(tracking,'Parar seguimiento',lambda:app.hand.submit('track',False)).pack(side='left',padx=3)
    app.label(hand,'Sideral según calibración del firmware.\nPosición calculada; sin encoders.',size=8,color='muted',justify='center').pack(pady=6)
    outer,goto=app.card(mid,'Ir a coordenadas de fecha','APUNTADO')
    outer.pack(side='left',fill='both',expand=True)
    if not hasattr(app,'mount_ra'): app.mount_ra=tk.StringVar();app.mount_dec=tk.StringVar()
    for label,var in [('AR JNow · hh:mm:ss',app.mount_ra),('DEC JNow · ±gg:mm:ss',app.mount_dec)]:
        app.label(goto,label,size=9,color='muted').pack(anchor='w',pady=(3,4));ttk.Entry(goto,textvariable=var,width=22).pack(fill='x')
    def manual_goto():
        try:
            ra=parse_angle(app.mount_ra.get(),True)/15;dec=parse_angle(app.mount_dec.get())
            if messagebox.askyesno('Mover la montura','¿Mover a estas coordenadas de fecha? Confirma Home, hora, ubicación y espacio libre en el OAT.',parent=app.root): app.hand.submit('goto',ra,dec)
        except ValueError as exc: app.write(str(exc))
    app.button(goto,'Ir a estas coordenadas',manual_goto,primary=True).pack(fill='x',pady=(12,6))
    def home():
        if messagebox.askyesno('Volver a Home','¿Mover a la referencia Home que ya tiene el OAT? Comprueba que el recorrido esté libre.',parent=app.root): app.hand.submit('home')
    app.button(goto,'Volver a Home existente',home).pack(fill='x',pady=3)
    app.button(goto,'Salir de Park',lambda:app.hand.submit('park',False)).pack(fill='x',pady=3)
    app.label(goto,'No redefine Home ni busca sensores.\nEl LCD conserva su uso autónomo.',size=8,color='muted',justify='left').pack(anchor='w',pady=8)
    app.activity()
    update(app,app.mount_snapshot)

def update(app,snapshot):
    app.mount_snapshot=snapshot
    app.mount_observed_utc=datetime.now(timezone.utc).isoformat()
    def values(name): return next((v['values'] for k,v in snapshot.items() if k.endswith('/'+name)),{})
    connection=values('CONNECTION')
    connection_prop=next((p for k,p in snapshot.items() if k.endswith('/CONNECTION')),{} )
    if connection.get('CONNECT')!='On' or connection_prop.get('state')=='Alert':
        app.mount_status.set('Desconectada · selecciona el puerto y pulsa Conectar')
        app.mount_badge.set('Montura: desconectada');return
    app.mount_badge.set('Montura: conectada')
    coords=values('EQUATORIAL_EOD_COORD');firmware=values('FIRMWARE_INFO');state=values('OAT_STATUS')
    sample=values('OAT_SITE_TIME')
    sample_prop=next((p for k,p in snapshot.items() if k.endswith('/OAT_SITE_TIME')), {})
    if sample.get('UTC') and sample_prop.get('state')=='Ok' and getattr(app,'mount_time_sample',None)!=sample.get('MONOTONIC'):
        app.mount_time_sample=sample['MONOTONIC']
        from .timekeeping import import_mount_time
        try:
            imported=import_mount_time(sample)
            if imported.get('use_mount_time',True):
                app.write('Hora UTC y ubicación importadas de OAT. La confirmación GPS se consulta en el LCD.')
                if app.current_page=='atlas':
                    from .atlas_ui import refresh_visibility,refresh_details
                    refresh_visibility(app);refresh_details(app)
        except Exception as exc: app.write('No se usó la hora/ubicación OAT: '+str(exc))
    device=next(iter(snapshot),'Montura').split('/')[0];app.mount_fields['device'].set(device)
    text=f"{device} · {firmware.get('VERSION','versión del controlador')} · {state.get('STATE','conectada')}"
    if coords:
        try: text+=f"\nAR {format_ra(float(coords['RA'])*15)}   DEC {format_dec(float(coords['DEC']))}   · fecha"
        except ValueError: pass
    from .timekeeping import clock_snapshot,load_settings
    clock=clock_snapshot(load_settings(),float(coords['RA']) if coords.get('RA') else None)
    text+='\n'+clock['local'][:19].replace('T',' ')+' · '+clock['source']
    if clock['sidereal_hours'] is not None: text+=f" · TSL {format_ra(clock['sidereal_hours']*15)} · HA apuntado {clock['ha_hours']:+.2f} h" if clock['ha_hours'] is not None else ''
    if sample.get('OAT_HA_HOURS'): text+=f"\nHA OAT informado {float(sample['OAT_HA_HOURS']):.2f} h (referencia polar, distinto del HA del objeto)"
    app.mount_status.set(text)
