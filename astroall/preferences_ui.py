"""One friendly settings window for optics, JPEG correction and appearance."""
import tkinter as tk
from tkinter import ttk
from .preferences import load,save
from .recommendations import SENSORS

def settings_window(app):
    dialog=tk.Toplevel(app.root);dialog.title('Astro One4All · Configuración');dialog.configure(bg=app.colors['bg'])
    body=app.frame(dialog);body.pack(fill='both',expand=True,padx=22,pady=18)
    app.label(body,'Ajusta tu observatorio.',size=16,bold=True).pack(anchor='w',pady=(0,12))
    tabs=ttk.Notebook(body);tabs.pack(fill='both',expand=True);values=load();fields={}
    for title,entries in [('Cámara y lente',[('sensor','Formato del sensor',list(SENSORS)),('focal','Focal que usarás / mm',None),('iso','ISO inicial',['Cámara','100','200','400','800','1600','3200','6400']),('minutes','Integración sugerida / min',['15','30','60','90','120']),('delay','Pausa entre fotos / s',None)]),
                          ('Corrección por JPG',[('jpg_correction','Corregir encuadre con mi cámara',True),('jpg_every','Comprobar cada / fotos',['5','10','20','30']),('jpg_exposure','Foto de comprobación / s',['1','2','5','10']),('tolerance_arcsec','Error permitido / segundos de arco',None)]),
                          ('Pantalla y equipo',[('night_start','Iniciar en modo rojo',True),('show_internal_guide','Mostrar también cámaras integradas',True)])]:
        panel=app.frame(tabs,'card');tabs.add(panel,text=title)
        for key,label,choices in entries:
            line=app.frame(panel,'card');line.pack(fill='x',padx=14,pady=7)
            if choices is True:
                variable=tk.BooleanVar(value=values[key]);ttk.Checkbutton(line,text=label,variable=variable).pack(anchor='w')
            else:
                variable=tk.StringVar(value=str(values[key]));app.label(line,label,size=9).pack(anchor='w',pady=(0,4))
                widget=ttk.Combobox(line,textvariable=variable,values=choices,width=40,state='readonly' if key in ('sensor','iso') else 'normal') if choices else ttk.Entry(line,textvariable=variable,width=43)
                widget.pack(fill='x')
            fields[key]=variable
        if title=='Corrección por JPG':
            app.label(panel,'Sin cámara guía: comprueba un JPG de tus propias tomas entre exposiciones.\nSi hay que mover, toma otra foto para verificar. No corrige durante una exposición.\n1 minuto de arco = 60 segundos de arco.',size=9,color='muted',wraplength=590,justify='left').pack(anchor='w',padx=14,pady=12)
        if title=='Cámara y lente':app.label(panel,'R50: APS-C Canon. Cambia la focal físicamente en el lente.\nLa recomendación del atlas se puede modificar antes de preparar el plan.',size=9,color='muted',wraplength=590,justify='left').pack(anchor='w',padx=14,pady=12)
        if title=='Pantalla y equipo':
            from .atlas_ui import site_window
            app.button(panel,'Ubicación, hora y GPS',lambda:site_window(app)).pack(anchor='w',padx=14,pady=12)
            app.label(panel,'Las cámaras internas se ocultan para evitar confundirlas con la USB.\nEl enfoque manual y el seguimiento OAT funcionan sin cámara guía.',size=9,color='muted',wraplength=590,justify='left').pack(anchor='w',padx=14,pady=12)
    note=tk.StringVar(value='Los cambios se guardan para las próximas sesiones. No se mueve ningún equipo.')
    app.label(body,variable=note,size=9,color='accent',wraplength=610,justify='left').pack(anchor='w',pady=12)
    def commit():
        if app.busy:note.set('Termina la tarea en curso antes de guardar ajustes.');return
        try:
            value=save({k:v.get() for k,v in fields.items()})
            if hasattr(app,'guide_show_internal'):app.guide_show_internal.set(value['show_internal_guide'])
            if hasattr(app,'atlas'):
                a=app.atlas;a['sensor'].set(value['sensor']);a['focal'].set(str(value['focal']))
                from .atlas_ui import update_proposal
                update_proposal(app)
            app.write('Configuración guardada. Los planes ya preparados conservan su focal y sus ajustes.');dialog.destroy()
        except Exception as exc:note.set(str(exc))
    app.button(body,'Guardar configuración',commit,primary=True).pack(anchor='e')
