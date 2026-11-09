"""PHD2 control and a bounded error graph, without streaming image BLOBs."""
import shutil
import subprocess
import time
import tkinter as tk
from tkinter import ttk
from .guiding import PHD2Client

def guide_page(app):
    if not hasattr(app,'guide_state'):
        app.guide_state=tk.StringVar(value='Sin consultar · cámara guía aún por validar')
        app.guide_ra_only=tk.BooleanVar(value=False);app.guide_amount=tk.StringVar(value='2');app.guide_snapshot=None
    outer,body=app.card(app.content,'Guiado con una cámara independiente','PHD2 · EQUIPO REAL O SIMULADOR EXPLÍCITO')
    outer.pack(fill='x')
    app.label(body,'Primero conecta la montura y elige abajo la cámara USB.\nCon PHD2 cerrado, prepara su perfil; después ábrelo y conecta el equipo.',size=10,justify='left',wraplength=730).pack(anchor='w',pady=(0,12))
    row=app.frame(body,'card');row.pack(fill='x')
    def launch():
        executable=shutil.which('phd2')
        if not executable: app.write('PHD2 no está instalado en este sistema; utiliza la nueva Live USB.');return
        from .guide_camera import profile
        from .guide_profile import prepare,phd_running
        from .mount_service import profile as mount_profile
        saved=profile();cfg=mount_profile();focal=app.guide_focal.get();pixel=app.guide_pixel.get();allow_internal=app.guide_show_internal.get()
        def operation():
            if phd_running(): return 'PHD2 ya está abierto. Ciérralo y vuelve a pulsar Abrir PHD2 para aplicar el perfil USB correcto.'
            if not saved.get('indi_device'): raise RuntimeError('Busca, identifica y conecta primero tu webcam USB.')
            from .guide_camera import selected_device
            current=selected_device(saved['path'])
            if current.get('role') in ('internal','possibly_internal') and not allow_internal:
                raise RuntimeError('El perfil guardado corresponde a la integrada. Pulsa Identificar USB y conecta tu webcam antes de abrir PHD2.')
            prepare(saved['indi_device'],cfg['device'],focal,pixel,camera_id=saved['path']+'|'+saved['bus'])
            subprocess.Popen([executable],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            return 'PHD2 abierto con cámara USB, vídeo monocromo y montura INDI. Pulsa Conectar equipo en PHD2.'
        app.task('Abriendo PHD2 con tu equipo…',operation)
    app.button(row,'Abrir PHD2',launch,primary=True).pack(side='left')
    app.button(row,'Consultar / gráfica 15 s',lambda:monitor(app)).pack(side='left',padx=8)
    app.button(row,'Guiar / calibrar si hace falta',lambda:action(app,'guide')).pack(side='left')
    app.button(row,'Detener guiado',lambda:action(app,'stop'),danger=True).pack(side='right')
    app.label(body,variable=app.guide_state,color='accent',size=10).pack(anchor='w',pady=(14,0))
    cameras=app.frame(body,'card');cameras.pack(fill='x',pady=(8,0))
    from .mount_service import add_guide_camera
    from .guide_camera import video_devices,profile
    if not hasattr(app,'guide_camera_choice'):
        app.guide_camera_choice=tk.StringVar();app.guide_devices=[]
        app.guide_focal=tk.StringVar();app.guide_pixel=tk.StringVar()
        from .preferences import load
        app.guide_show_internal=tk.BooleanVar(value=load()['show_internal_guide'])
    selector=ttk.Combobox(cameras,textvariable=app.guide_camera_choice,state='readonly',width=50)
    selector.pack(side='left',fill='x',expand=True,padx=(0,8))
    def found(devices,identified=None):
        app.guide_devices=devices
        if not selector.winfo_exists(): return
        visible=[d for d in devices if app.guide_show_internal.get() or d.get('role')!='internal']
        selector.configure(values=[d['label'] for d in visible])
        confirmed=[d for d in visible if d.get('role')=='external_confirmed']
        saved=profile();selected=identified or next((d for d in visible if d['path']==saved.get('path') and d['bus']==saved.get('bus')),None)
        if selected is None and len(confirmed)==1: selected=confirmed[0]
        if selected is None and len(visible)==1:selected=visible[0]
        app.guide_camera_choice.set(selected['label'] if selected else '')
        app.write(f'{len(visible)} cámaras USB disponibles; {len(devices)-len(visible)} integradas ocultas. Si no reconoces la Acteck, pulsa Identificar USB.')
    def refresh():
        from .guide_camera import scan_devices
        app.task('Buscando cámaras…',scan_devices,found)
    app.button(cameras,'Buscar cámaras',refresh).pack(side='left')
    ttk.Checkbutton(cameras,text='Ver integrada',variable=app.guide_show_internal,command=lambda:found(app.guide_devices)).pack(side='left',padx=(8,0))
    cameras=app.frame(body,'card');cameras.pack(fill='x',pady=(8,0))
    def connect_camera():
        selected=next((d for d in app.guide_devices if d['label']==app.guide_camera_choice.get()),None)
        if not selected: app.write('Pulsa Buscar cámaras y elige la cámara USB; no se selecciona ninguna automáticamente.');return
        app.task('Conectando la cámara elegida…',lambda:add_guide_camera(path=selected['path'],expected=selected))
    app.button(cameras,'Conectar cámara',connect_camera,primary=True).pack(side='left')
    from .guide_usb_ui import identify_usb,show_preview
    from .guide_preview import capture_preview
    def test_usb():
        selected=next((d for d in app.guide_devices if d['label']==app.guide_camera_choice.get()),None)
        if not selected:app.write('Pulsa Buscar cámaras y elige la cámara USB.');return
        def operation():
            add_guide_camera(path=selected['path'],expected=selected)
            return capture_preview(stop=app.stop)
        app.task('Conectando y recibiendo imagen USB…',operation,lambda result:show_preview(app,result))
    app.button(cameras,'Probar imagen USB',test_usb).pack(side='left',padx=8)
    app.button(cameras,'Identificar USB',lambda:identify_usb(app,found)).pack(side='left')
    app.button(cameras,'Simulada',lambda:app.task('Preparando cámara simulada…',lambda:add_guide_camera('indi_simulator_ccd'))).pack(side='right')
    app.label(body,'La integrada se oculta. Identificar USB reconoce tu webcam al desconectarla y volverla a conectar.',size=9,color='muted').pack(anchor='w',pady=(6,0))
    settings=app.frame(body,'card');settings.pack(fill='x',pady=(8,0))
    for title,var in [('Focal guía / mm',app.guide_focal),('Píxel / µm',app.guide_pixel)]:
        app.label(settings,title,size=9,color='muted').pack(side='left',padx=(0,5))
        ttk.Entry(settings,textvariable=var,width=7).pack(side='left',padx=(0,10))
    def prepare_profile():
        from .guide_profile import prepare
        from .mount_service import profile as mount_profile
        saved=profile()
        if not saved.get('indi_device'): app.write('Conecta primero la cámara elegida.');return
        cfg=mount_profile();focal=app.guide_focal.get();pixel=app.guide_pixel.get();allow_internal=app.guide_show_internal.get()
        def operation():
            from .guide_camera import selected_device
            current=selected_device(saved['path'])
            if current.get('role') in ('internal','possibly_internal') and not allow_internal:
                raise RuntimeError('El perfil guardado es de la integrada. Identifica y conecta la webcam USB.')
            return prepare(saved['indi_device'],cfg['device'],focal,pixel,camera_id=saved['path']+'|'+saved['bus'])
        app.task('Preparando perfil PHD2…',operation)
    app.button(settings,'Preparar perfil PHD2',prepare_profile).pack(side='right')
    outer,graph=app.card(app.content,'Error de guiado','ÚLTIMAS 120 MUESTRAS')
    outer.pack(fill='both',expand=True,pady=(14,0))
    app.guide_canvas=tk.Canvas(graph,bg=app.colors['preview'],height=70,highlightthickness=0);app.guide_canvas.pack(fill='both',expand=True)
    app.guide_canvas.bind('<Configure>',lambda e:draw(app))
    row=app.frame(graph,'card');row.pack(fill='x',pady=12)
    app.label(row,'Dither / píxeles guía',size=9,color='muted').pack(side='left')
    ttk.Entry(row,textvariable=app.guide_amount,width=6).pack(side='left',padx=8)
    ttk.Checkbutton(row,text='Solo AR',variable=app.guide_ra_only).pack(side='left')
    app.button(row,'Aplicar dither y estabilizar',lambda:action(app,'dither')).pack(side='right')
    app.label(graph,'El RMS solo se muestra en segundos de arco si PHD2 entrega una escala válida.\nLa Canon comprueba el encuadre entre exposiciones; no guía durante una exposición larga.',size=9,color='muted',justify='left').pack(anchor='w')
    app.activity();draw(app)

def status(app,value):
    app.guide_snapshot=value;rms=value['total_rms']
    app.guide_state.set(value['state']+(' · estabilizando' if value['settling'] else '')+(f" · RMS {rms:.2f} {value['unit']}" if rms is not None else ' · sin muestras'))
    draw(app)
def monitor(app):
    def operation():
        with PHD2Client() as client:
            try: client.request('get_pixel_scale')
            except Exception: pass
            deadline=time.monotonic()+15
            while time.monotonic()<deadline and not app.stop.is_set():
                client.read();value=client.snapshot();app.post(lambda v=value:status(app,v))
        return 'Gráfica actualizada. La captura de imágenes sigue en PHD2.'
    app.task('Recibiendo guiado…',operation)
def action(app,kind):
    try: amount=float(app.guide_amount.get());ra_only=app.guide_ra_only.get()
    except ValueError: app.write('Dither debe ser numérico.');return
    def operation():
        with PHD2Client() as client:
            callback=lambda value:app.post(lambda v=value:status(app,v))
            if kind=='guide': client.start_guiding(stop=app.stop,progress=callback)
            elif kind=='dither': client.dither(amount,ra_only,stop=app.stop,progress=callback)
            elif kind=='stop': client.request('stop_capture')
            return 'PHD2: orden completada y confirmada.'
    if kind=='stop' and app.busy:
        app.stop.set();app.write('Deteniendo la tarea; espera a que termine antes de reanudar guiado.');return
    app.task('PHD2 · esperando confirmación…',operation)
def draw(app):
    c=getattr(app,'guide_canvas',None);value=getattr(app,'guide_snapshot',None)
    if not c or not c.winfo_exists(): return
    c.configure(bg=app.colors['preview']);c.delete('all');w=max(100,c.winfo_width());h=max(60,c.winfo_height());center=h/2
    c.create_line(0,center,w,center,fill=app.colors['border'])
    if not value or len(value['steps'])<2:
        c.create_text(w/2,h/2,text='Conecta PHD2 para ver las correcciones.',fill=app.colors['muted']);return
    steps=value['steps'];scale=value['pixel_scale'] or 1;extent=max(1,max(abs(x)*scale for row in steps for x in row));yscale=(h/2-25)/extent
    for axis,color in [(0,'accent'),(1,'success')]:
        coords=[]
        for i,row in enumerate(steps): coords.extend((10+i/(len(steps)-1)*(w-20),center-row[axis]*scale*yscale))
        c.create_line(*coords,fill=app.colors[color],width=2)
    c.create_text(12,12,text=f"AR / DEC · ±{extent:.1f} {value['unit']}",anchor='nw',fill=app.colors['muted'])
