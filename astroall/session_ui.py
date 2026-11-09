"""Reviewable capture blocks and their execution through the camera worker."""
from dataclasses import asdict
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from .session import Block,execute,recenter,state_path

def session_page(app):
    if not hasattr(app,'sequence'):
        from .preferences import load
        pref=load()
        app.sequence={'blocks':[Block()], 'exposure':tk.StringVar(value='30'),'count':tk.StringVar(value='10'),'iso':tk.StringVar(value='Cámara'),
                      'delay':tk.StringVar(value='3'),'type':tk.StringVar(value='Light'),'guide':tk.BooleanVar(value=False),
                      'dither':tk.StringVar(value='0'),'recenter':tk.StringVar(value='0'),'goto':tk.BooleanVar(value=False),
                      'jpg_correct':tk.BooleanVar(value=False),'field_deg':tk.StringVar(value=''),'framing':{},
                      'recommendation':tk.StringVar(),'target_text':tk.StringVar(value='Campo actual · elige un objetivo en Atlas')}
        app.sequence['recenter'].set(str(pref['jpg_every']))
    s=app.sequence
    if s['framing']:
        f=s['framing'];s['recommendation'].set(f"Lente a {f['focal']:g} mm · {f['sensor']} · ajusta la focal físicamente y comprueba el enfoque antes de iniciar.")
    header=app.frame(app.content);header.pack(fill='x',pady=(0,12))
    targets=getattr(app,'plan_targets',[])
    s['target_text'].set(f"{targets[0].label} · {len(targets)} encuadre(s)" if targets else 'Campo actual · listo para fotos de prueba')
    app.label(header,variable=s['target_text'],size=10,color='accent',anchor='w',wraplength=650).pack(side='left',fill='x',expand=True)
    app.button(header,'Atlas',lambda:app.show('atlas')).pack(side='right')
    clear=app.button(header,'Quitar objetivo',lambda:clear_target(app));clear.pack(side='right',padx=(6,8))
    if not targets:clear.state(['disabled'])
    work=app.frame(app.content);work.pack(fill='both',expand=True)
    outer,view=app.card(work,'Último JPG','RAW / CR3 EN LA SD DE LA CÁMARA')
    outer.pack(side='left',fill='both',expand=True,padx=(0,14))
    app.preview=tk.Canvas(view,bg=app.colors['preview'],height=220,highlightthickness=0)
    app.preview.pack(fill='both',expand=True);app.preview.bind('<Configure>',lambda e:app.render_preview())
    actions=app.frame(view,'card');actions.pack(fill='x',pady=10)
    app.button(actions,'Abrir JPG',app.open_jpeg).pack(side='left')
    app.button(actions,'Plate solving',app.solve_current).pack(side='left',padx=5)
    app.button(actions,'Foto de prueba · 1 s',lambda:app.test_camera(False)).pack(side='left')
    app.button(actions,'Centrar',lambda:center(app)).pack(side='right')
    app.label(view,variable=app.progress_text,size=9,color='muted').pack(anchor='w')
    app.label(view,variable=s['recommendation'],size=8,color='accent',wraplength=550,justify='left').pack(fill='x',pady=(4,0))
    app.progress=ttk.Progressbar(view,maximum=100,value=100*app.completed/max(1,app.requested));app.progress.pack(fill='x',pady=(8,0))
    outer,plan=app.card(work,'Plan de captura','SECUENCIAS')
    outer.pack(side='left',fill='y')
    editor=ttk.Notebook(plan);editor.pack(fill='x')
    general=ttk.Frame(editor,padding=5);block_list=ttk.Frame(editor,padding=5)
    editor.add(general,text='Exposición');editor.add(block_list,text='Bloques')
    grid=app.frame(general,'card');grid.pack(fill='x')
    for i,(key,label,width,choices) in enumerate([('exposure','Exposición / s',9,['1','2','5','10','15','20','30','60','120','180','300']),('count','Cantidad',7,None),('iso','ISO',9,['Cámara','100','200','400','800','1600','3200','6400']),('delay','Pausa / s',7,None)]):
        box=app.frame(grid,'card');box.grid(row=i//2,column=i%2,padx=(0,10),pady=2,sticky='ew')
        app.label(box,label,size=8,color='muted').pack(anchor='w')
        widget=ttk.Combobox(box,textvariable=s[key],values=choices,width=width) if choices else ttk.Entry(box,textvariable=s[key],width=width)
        widget.pack(pady=4)
    line=app.frame(general,'card');line.pack(fill='x',pady=4)
    ttk.Combobox(line,textvariable=s['type'],values=['Light','Dark','Flat','Bias'],state='readonly',width=8).pack(side='left')
    app.button(line,'+ Bloque',lambda:add_block(app)).pack(side='right')
    tree=ttk.Treeview(block_list,columns=('exp','count','iso'),show='tree headings',height=4,selectmode='browse')
    tree.heading('#0',text='Tipo');tree.column('#0',width=46,stretch=False)
    for key,title,width in [('exp','s',53),('count','Fotos',45),('iso','ISO',60)]: tree.heading(key,text=title);tree.column(key,width=width,stretch=False)
    tree.pack(fill='x',pady=5);s['tree']=tree;refresh_blocks(app)
    buttons=app.frame(block_list,'card');buttons.pack(fill='x')
    app.button(buttons,'Quitar',lambda:remove_block(app)).pack(side='left')
    app.button(buttons,'Guardar',lambda:save_plan(app)).pack(side='left',padx=4)
    app.button(buttons,'Abrir',lambda:load_plan(app)).pack(side='right')
    notebook=ttk.Notebook(plan);notebook.pack(fill='x',pady=(8,6))
    guide_options=ttk.Frame(notebook,padding=5);options=ttk.Frame(notebook,padding=5)
    notebook.add(guide_options,text='Cámara guía');notebook.add(options,text='Corrección JPG');notebook.select(options)
    ttk.Checkbutton(options,text='Apuntar al objetivo al iniciar',variable=s['goto']).pack(anchor='w')
    ttk.Checkbutton(guide_options,text='Exigir guiado PHD2',variable=s['guide']).pack(anchor='w')
    dither_row=ttk.Frame(guide_options);dither_row.pack(fill='x',pady=4)
    ttk.Label(dither_row,text='Dither cada / fotos').pack(side='left');ttk.Entry(dither_row,textvariable=s['dither'],width=5).pack(side='right')
    ttk.Checkbutton(options,text='Corregir con JPG de mi cámara',variable=s['jpg_correct']).pack(anchor='w')
    cadence=ttk.Frame(options);cadence.pack(fill='x',pady=2)
    ttk.Label(cadence,text='Cada / fotos').pack(side='left');ttk.Entry(cadence,textvariable=s['recenter'],width=5).pack(side='right')
    app.capture_button=app.button(plan,'Iniciar plan',lambda:start(app),primary=True);app.capture_button.pack(fill='x')
    if app.busy: app.capture_button.state(['disabled'])
    app.button(plan,'Detener captura / cerrar Bulb',app.stop.set,danger=True).pack(fill='x',pady=(7,0))
    app.label(plan,'M · RAW + JPG · enfoque manual\nGuiado opcional · Bulb según cámara.',size=8,color='muted',justify='left').pack(anchor='w',pady=(6,0))
    app.activity()

def clear_target(app):
    if app.busy:
        app.write('Primero detén la tarea y espera a que termine para quitar el objetivo.');return False
    s=app.sequence
    app.plan_targets=[];app.selected_target=None
    s['goto'].set(False);s['jpg_correct'].set(False);s['field_deg'].set('');s['framing']={};s['recommendation'].set('')
    app.show('session')
    app.write('Objetivo retirado. Fotografiarás el campo actual sin GoTo ni centrado automático. Se conservaron exposición, bloques y fotos.');return True


def current_block(app):
    s=app.sequence;b=Block(int(s['count'].get()),float(s['exposure'].get()),s['iso'].get().strip(),s['type'].get(),float(s['delay'].get()));b.validate();return b
def add_block(app):
    try:
        app.sequence['blocks'].append(current_block(app));refresh_blocks(app)
    except Exception as exc: app.write(str(exc))
def refresh_blocks(app):
    s=app.sequence;tree=s['tree'];tree.delete(*tree.get_children())
    for i,b in enumerate(s['blocks']): tree.insert('','end',iid=str(i),text=b.frame_type,values=(f'{b.exposure:g}',b.count,b.iso))
    app.requested=max(1,sum(b.count for b in s['blocks'])*max(1,len(getattr(app,'plan_targets',[]))))
def remove_block(app):
    selection=app.sequence['tree'].selection()
    if selection: del app.sequence['blocks'][int(selection[0])];refresh_blocks(app)
def save_plan(app):
    path=filedialog.asksaveasfilename(title='Guardar plan',defaultextension='.json',initialfile='mi-noche.json')
    if path:
        s=app.sequence
        data={'version':1,'blocks':[asdict(b) for b in s['blocks']],'targets':[asdict(t) for t in app.plan_targets],
              'options':{'goto':s['goto'].get(),'guide':s['guide'].get(),'dither':int(s['dither'].get()),'recenter':int(s['recenter'].get()),'jpg_correct':s['jpg_correct'].get(),'field_deg':float(s['field_deg'].get() or app.width.get()),'framing':s['framing']}}
        Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');app.write('Plan guardado. Su apertura no inicia capturas ni movimientos.')
def load_plan(app):
    path=filedialog.askopenfilename(title='Abrir plan',filetypes=[('Plan Astro One4All','*.json')])
    if not path: return
    try:
        from .catalog import Target
        file=Path(path)
        if file.stat().st_size>1024*1024: raise ValueError('Archivo de plan demasiado grande.')
        data=json.loads(file.read_text(encoding='utf-8'))
        if data['version']!=1 or not 1<=len(data['blocks'])<=100 or len(data.get('targets',[]))>81: raise ValueError('Formato de plan inválido.')
        blocks=[Block(**x) for x in data['blocks']]
        for b in blocks: b.validate()
        targets=[Target(**x) for x in data.get('targets',[])]
        app.sequence['blocks']=blocks;app.plan_targets=targets;app.selected_target=targets[0] if targets else None
        options=data.get('options',{})
        for key in ('goto','guide'):
            value=options.get(key,False)
            if not isinstance(value,bool): raise ValueError('Opción de plan inválida.')
            app.sequence[key].set(value)
        for key in ('dither','recenter'): app.sequence[key].set(str(options.get(key,0)))
        app.sequence['jpg_correct'].set(bool(options.get('jpg_correct',options.get('recenter',0))))
        if 'field_deg' in options:app.sequence['field_deg'].set(str(float(options['field_deg'])))
        app.sequence['framing']=options.get('framing',{})
        first=blocks[0]
        for key,value in [('count',first.count),('exposure',first.exposure),('iso',first.iso),('type',first.frame_type),('delay',first.delay)]: app.sequence[key].set(str(value))
        app.show('session');app.write('Plan cargado. Revisa las tomas y pulsa Iniciar cuando estés listo.')
    except Exception as exc: app.write('No se abrió el plan: '+str(exc))
def emit(app,event):
    if event.get('event')=='shot': app.messages.put(('shot',event))
    elif event.get('event')=='center':
        app.post(lambda e=event:app.write(f"Centrado · error {e['error_arcsec']:.0f}″ · intento {e['attempt']}"))
        def preview(e=event):
            app.preview_path=e['jpeg']
            if app.current_page=='session':app.render_preview()
        app.post(preview)
    else: app.post(lambda e=event:app.write(e.get('message',e)))
def start(app):
    s=app.sequence
    try:
        # A single block tracks the visible editor, so changing exposure is immediately useful.
        if len(s['blocks'])==1: s['blocks']=[current_block(app)];refresh_blocks(app)
        blocks=list(s['blocks']);targets=list(app.plan_targets);guide=s['guide'].get();dither=int(s['dither'].get());center_every=int(s['recenter'].get()) if s['jpg_correct'].get() else 0;field=float(s['field_deg'].get() or app.width.get());goto_first=s['goto'].get()
        from .preferences import load
        pref=load();center_options={'exposure':pref['jpg_exposure'],'tolerance_arcsec':pref['tolerance_arcsec']}
        if not blocks: raise ValueError('Añade al menos un bloque al plan.')
        if center_every and not targets:raise ValueError('Elige un objeto en Atlas y pulsa Agregar al programa para corregir el encuadre con JPG.')
        kinds=set(b.frame_type for b in blocks)
        if len(kinds)>1: raise ValueError('Ejecuta Light, Dark, Flat y Bias en planes separados para poder colocar la tapa o el panel de luz.')
        if len(targets)>1 and not center_every: raise ValueError('Activa Centrar cada (por ejemplo 10) para ejecutar y verificar un mosaico.')
        if targets and kinds=={'Light'} and not (goto_first or center_every):
            raise ValueError('Activa Apuntar al objetivo al iniciar, o retira el objetivo para fotografiar el campo actual.')
        if center_every:
            from .solve import indexes_available
            if not indexes_available([Path.home()/'astroall-data/indexes','/usr/share/astrometry']):
                raise ValueError('Faltan índices de plate solving para centrar. Instálalos antes de iniciar este plan.')
        summary=f"{sum(b.count for b in blocks)*max(1,len(targets))} fotos · RAW + JPG en la tarjeta de la cámara."
        if goto_first and not center_every: summary+='\nLa montura apuntará al objetivo usando Home y las coordenadas OAT. Revisa el encuadre con una toma de prueba.'
        if center_every: summary+='\nEl plan moverá la montura al objetivo y verificará el centrado con JPG.'
        if center_every:summary+=' Las fotos adicionales de comprobación no cuentan en el total del plan.'
        if kinds!={'Light'}: summary+='\nConfirma tapa o iluminación y exposición correctas para '+next(iter(kinds))+'.'
        if not messagebox.askyesno('Iniciar plan de captura',summary+'\n¿Iniciar?',parent=app.root): return
        app.completed=0;app.requested=sum(b.count for b in blocks)*max(1,len(targets))
        app.task('Ejecutando plan de captura…',lambda:execute(blocks,targets,guide,dither,center_every,field,app.stop,lambda e:emit(app,e),goto_first=goto_first,recenter_options=center_options),lambda result:app.write(f"Plan {result['status']} · {result['completed']} de {result['total']} tomas confirmadas."))
    except Exception as exc: app.write(str(exc))
def center(app):
    target=getattr(app,'selected_target',None)
    if not target: app.write('Elige un objetivo en Atlas y pulsa Al plan.');return
    try:
        field=float(app.sequence['field_deg'].get() or app.width.get())
        from .preferences import load
        pref=load()
        if messagebox.askyesno('Centrado con JPG',f"¿Corregir el encuadre de {target.label}?\nSe tomarán JPG de prueba de {pref['jpg_exposure']:g} s y se corregirán errores de hasta 2°. No cambia la referencia Home.",parent=app.root):
            app.task('Centrando con fotos de prueba…',lambda:recenter(target,field,stop=app.stop,emit=lambda e:emit(app,e),exposure=pref['jpg_exposure'],tolerance_arcsec=pref['tolerance_arcsec']),app.write)
    except Exception as exc: app.write(str(exc))
