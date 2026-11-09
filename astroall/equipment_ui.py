"""Compact equipment selection; saving never connects or moves hardware."""
import tkinter as tk
from tkinter import ttk
from .equipment import load,save,inventory
from .mount_service import profile,save_profile,serial_ports

AUTO='Detectar automáticamente'

def equipment_page(app):
    if not hasattr(app,'equipment_fields'):
        settings=load();mount=profile()
        app.equipment_fields={'port':tk.StringVar(value=mount['port']),
            'camera':tk.StringVar(value=(settings['main_model']+' · '+settings['main_port']) if settings['main_model'] else AUTO),
            'guide_enabled':tk.BooleanVar(value=settings['guide_enabled']),
            'guide':tk.StringVar(value=settings['guide_path'] or 'Sin seleccionar'),
            'notice':tk.StringVar(value='Elige tu equipo. La cámara guía es opcional y el enfoque es manual.')}
        app.equipment_inventory={'ports':serial_ports(),'cameras':[],'guide':[]}
    fields=app.equipment_fields;devices=app.equipment_inventory
    from .preferences import load as preferences
    def allowed(items):return [d for d in items if preferences()['show_internal_guide'] or d.get('role')!='internal']
    intro,body=app.card(app.content,'')
    intro.pack(fill='x')
    app.label(body,variable=fields['notice'],size=9,color='muted',justify='left',wraplength=940).pack(anchor='w')
    columns=app.frame(app.content);columns.pack(fill='both',expand=True,pady=(12,0))
    outer,core=app.card(columns,'Lo esencial','01 / SESIÓN BÁSICA')
    outer.pack(side='left',fill='both',expand=True,padx=(0,12))
    from .mount_profiles import load as mount_bank
    from .mount_profiles_ui import manager
    bank=mount_bank();active=bank['profiles'][bank['selected']];mount=profile()
    line=app.frame(core,'card');line.pack(fill='x')
    app.label(line,'OpenAstroTracker',size=11,bold=True).pack(side='left')
    app.button(line,'Perfiles OAT',lambda:manager(app)).pack(side='right')
    app.label(core,f"{active['label']} · {active['board']}\nUSB · {mount['baud']} baudios · seguimiento sideral",size=8,color='muted',wraplength=420,justify='left').pack(anchor='w',pady=(3,7))
    port=ttk.Combobox(core,textvariable=fields['port'],values=devices['ports'],width=31);port.pack(fill='x')
    app.label(core,'Cámara principal',size=10,bold=True).pack(anchor='w',pady=(14,7))
    camera=ttk.Combobox(core,textvariable=fields['camera'],values=[AUTO]+[d['label'] for d in devices['cameras']],state='readonly',width=34);camera.pack(fill='x')
    app.label(core,'RAW + JPG en su tarjeta · previsualización ligera',size=8,color='muted').pack(anchor='w',pady=(5,0))
    app.label(core,variable=app.mount_badge,size=9,color='accent').pack(anchor='w',pady=(14,3))
    model=(getattr(app,'last_camera_info',None) or {}).get('model')
    app.label(core,('Cámara comprobada: '+model) if model else 'Cámara: todavía sin comprobar',size=9,color='muted',wraplength=430,justify='left').pack(anchor='w')
    row=app.frame(core,'card');row.pack(fill='x',pady=(14,0))
    app.button(row,'Conectar OAT',lambda:connect_mount(app),primary=True).pack(side='left')
    app.button(row,'Comprobar cámara',lambda:check_camera(app)).pack(side='right')
    outer,extra=app.card(columns,'Suma lo que necesites','02 / ACCESORIOS OPCIONALES')
    outer.pack(side='left',fill='both',expand=True)
    ttk.Checkbutton(extra,text='Tengo una cámara guía',variable=fields['guide_enabled']).pack(anchor='w')
    guide=ttk.Combobox(extra,textvariable=fields['guide'],values=[d['label'] for d in allowed(devices['guide'])],state='readonly',width=35);guide.pack(fill='x',pady=(8,5))
    app.label(extra,'Acteck USB hoy · otro modelo compatible después.\nSeleccionarla no activa guiado en tus planes.',size=9,color='muted',justify='left',wraplength=430).pack(anchor='w')
    app.button(extra,'Configurar autoguiado',lambda:app.show('guide')).pack(anchor='w',pady=(12,14))
    app.label(extra,'Enfoque manual',size=11,bold=True).pack(anchor='w')
    app.label(extra,'Ajusta el lente y mide la nitidez con un JPG.\nNo necesitas enfocador motorizado.',size=9,color='muted',justify='left',wraplength=420).pack(anchor='w',pady=(6,0))
    app.button(extra,'Asistente de enfoque',lambda:app.show('focus')).pack(anchor='w',pady=(12,0))
    actions=app.frame(app.content);actions.pack(fill='x',pady=(12,0))
    def found(value):
        app.equipment_inventory=value
        if app.current_page!='system':return
        if not port.winfo_exists():app.show('system');return
        choices=allowed(value['guide'])
        port.configure(values=value['ports']);camera.configure(values=[AUTO]+[d['label'] for d in value['cameras']]);guide.configure(values=[d['label'] for d in choices])
        if len(value['ports'])==1 and not fields['port'].get():fields['port'].set(value['ports'][0])
        if len(value['cameras'])==1:fields['camera'].set(value['cameras'][0]['label'])
        selected=load().get('guide_path')
        known=next((d for d in choices if d['path']==selected),None)
        if known is None and len(choices)==1:known=choices[0]
        if known:fields['guide'].set(known['label'])
        elif not choices:fields['guide'].set('Sin cámara USB seleccionada')
        fields['notice'].set(f"{len(value['ports'])} puerto(s) de montura · {len(value['cameras'])} cámara(s) principal(es) · {len(value['guide'])} cámara(s) de vídeo. "+value.get('note',''))
    app.button(actions,'Buscar equipo',lambda:app.task('Buscando dispositivos conectados…',inventory,found)).pack(side='left')
    app.button(actions,'Guardar selección',lambda:save_selection(app),primary=True).pack(side='left',padx=8)
    app.label(actions,'Guardar conserva el perfil entre sesiones.',size=8,color='muted').pack(side='left',padx=6)
    tools,body=app.card(app.content,'Pruebas y herramientas')
    tools.pack(fill='x',pady=(12,0))
    row=app.frame(body,'card');row.pack(fill='x')
    from .doctor import report
    from .atlas_ui import site_window
    for title,command in [('Prueba foto · 1 s',lambda:app.test_camera(False)),('Prueba Bulb · 3 s',lambda:app.test_camera(True)),
                          ('Ubicación y hora',lambda:site_window(app)),('Comprobar sistema',lambda:app.task('Comprobando sistema…',report,app.on_report))]:
        app.button(row,title,command).pack(side='left',padx=(0,7))
    row=app.frame(body,'card');row.pack(fill='x',pady=(8,0))
    app.button(row,'Guardar diagnóstico',app.export_diagnostic).pack(side='left')
    app.button(row,'Apagar o reiniciar',app.power_dialog).pack(side='right')
    from .solve import solver_status
    solver=solver_status()
    app.label(body,solver['label']+' · Las pruebas toman fotos reales. M, RAW + JPG, enfoque manual.',size=8,color='accent' if solver['ready'] else 'muted',wraplength=940,justify='left').pack(anchor='w',pady=(8,0))

def save_selection(app):
    if app.busy:app.write('Termina la tarea en curso antes de cambiar el equipo seleccionado.');return False
    try:
        fields=app.equipment_fields;previous=load();devices=app.equipment_inventory;mount=profile();selected_port=fields['port'].get().strip()
        if getattr(getattr(app,'hand',None),'connecting',False):raise ValueError('Espera a que termine la conexión OAT antes de cambiar el perfil.')
        if getattr(app,'hand',None) and app.hand.client and selected_port!=mount['port']:
            raise ValueError('Desconecta la montura antes de cambiar su puerto. La conexión actual se conservó.')
        selected=next((d for d in devices['cameras'] if d['label']==fields['camera'].get()),None)
        if fields['camera'].get()==AUTO:previous.update(main_model='',main_port='')
        elif selected:previous.update(main_model=selected['model'],main_port=selected['port'])
        elif fields['camera'].get()!=previous['main_model']+' · '+previous['main_port']:
            raise ValueError('Busca equipo y selecciona una cámara principal de la lista.')
        guide=next((d for d in devices['guide'] if d['label']==fields['guide'].get()),None)
        previous.update(guide_enabled=fields['guide_enabled'].get(),guide_path=guide['path'] if guide else previous['guide_path'])
        save(previous);mount['port']=selected_port;save_profile(mount)
        if hasattr(app,'mount_fields'):app.mount_fields['port'].set(selected_port)
        if guide:
            from .guide_camera import save_profile as save_guide,profile as guide_profile
            old=guide_profile()
            save_guide(dict(old,**guide) if all(old.get(key)==guide[key] for key in ('path','name','bus')) else guide)
        if not previous['guide_enabled'] and hasattr(app,'sequence'):
            app.sequence['guide'].set(False);app.sequence['dither'].set('0')
        if not previous['guide_enabled'] and hasattr(app,'atlas'):app.atlas['guided'].set(False)
        fields['notice'].set('Perfil guardado. Enfoque manual; guiado opcional. Conecta cada equipo cuando vayas a utilizarlo.')
        app.write('Equipo seleccionado guardado. No se iniciaron capturas ni movimientos.');return True
    except Exception as exc:app.write(str(exc));return False

def connect_mount(app):
    if not save_selection(app):return
    app.show('mount');app.hand.submit('connect',profile())

def check_camera(app):
    if save_selection(app):app.task('Consultando la cámara seleccionada…',app.camera_info,app.on_camera)
