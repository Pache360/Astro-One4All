"""Connection profiles for OAT board variants, with no firmware writes."""
import tkinter as tk
from tkinter import ttk
from .mount_profiles import BOARDS,DRIVERS,load,create,activate
from .mount_service import serial_ports

def manager(app):
    dialog=tk.Toplevel(app.root);dialog.title('Astro One4All · Perfiles OAT');dialog.configure(bg=app.colors['bg'])
    body=app.frame(dialog);body.pack(fill='both',expand=True,padx=22,pady=18)
    app.label(body,'Una montura, su propio perfil.',size=16,bold=True).pack(anchor='w')
    app.label(body,'La placa ejecuta el firmware y controla sus motores. Este perfil elige la conexión.',size=9,color='muted',wraplength=600,justify='left').pack(anchor='w',pady=(6,12))
    bank=load();entries={value['label']+' · '+value['board']:key for key,value in bank['profiles'].items()}
    selected=tk.StringVar(value=next(label for label,key in entries.items() if key==bank['selected']))
    ttk.Combobox(body,textvariable=selected,values=list(entries),state='readonly',width=61).pack(fill='x')
    notice=tk.StringVar(value='Para cambiar de perfil, termina la captura y desconecta la montura.')
    def apply(key):
        hand=getattr(app,'hand',None)
        if app.busy or (hand and (hand.client or hand.connecting)):
            notice.set('La sesión sigue conectada. Desconecta la montura antes de cambiar de perfil.');return False
        cfg=activate(key)['connection'];app.mount_time_sample=None
        if hasattr(app,'mount_fields'):
            for name,value in cfg.items():
                if name in app.mount_fields:app.mount_fields[name].set(value)
        if hasattr(app,'equipment_fields'):app.equipment_fields['port'].set(cfg['port'])
        app.write('Perfil OAT activado. No se abrió el puerto ni se cambió la configuración de sus motores.')
        dialog.destroy()
        if app.current_page=='system':app.show('system')
        return True
    app.button(body,'Activar perfil seleccionado',lambda:apply(entries[selected.get()]),primary=True).pack(anchor='w',pady=(10,18))
    app.label(body,'Crear otro perfil',size=12,bold=True).pack(anchor='w',pady=(0,6))
    values={}
    for name,label,default,choices in [('label','Nombre','Otro OpenAstroTracker',None),('board','Placa','Sin especificar',BOARDS),
                                     ('driver','Controlador',next(iter(DRIVERS)),list(DRIVERS)),('port','Puerto serie USB','',serial_ports()),
                                     ('baud','Baudios del firmware','19200',['9600','19200','38400','57600','115200']),
                                     ('time','Hora y ubicación','PC confirmado',['PC confirmado','Leer del OAT / GPS si está instalado'])]:
        line=app.frame(body);line.pack(fill='x',pady=3);app.label(line,label,size=9,width=20,anchor='w').pack(side='left')
        var=tk.StringVar(value=default);values[name]=var
        widget=ttk.Combobox(line,textvariable=var,values=choices,state='normal' if name=='port' else 'readonly',width=40) if choices is not None else ttk.Entry(line,textvariable=var,width=42)
        widget.pack(side='left',fill='x',expand=True)
    def add():
        try:
            driver=DRIVERS[values['driver'].get()]
            cfg={'driver':driver,'device':'Telescope Simulator' if driver=='indi_simulator_telescope' else 'Astro One4All OAT' if driver=='indi_astroall_oat' else 'OpenAstroTech',
                 'port':values['port'].get().strip(),'baud':values['baud'].get()}
            hand=getattr(app,'hand',None)
            if app.busy or (hand and (hand.client or hand.connecting)):raise ValueError('Desconecta la montura antes de crear y activar otro perfil.')
            key=create(values['label'].get(),values['board'].get(),cfg,'pc' if values['time'].get()=='PC confirmado' else 'oat');apply(key)
        except Exception as exc:notice.set(str(exc))
    app.button(body,'Guardar y activar nuevo perfil',add,primary=True).pack(anchor='w',pady=(14,8))
    app.label(body,variable=notice,size=9,color='accent',wraplength=610,justify='left').pack(anchor='w',pady=6)
    app.label(body,'USB/serie · versión consultada al conectar · sin cambios de pines, EEPROM, Home o calibración.\nOtras familias de firmware y conexiones Wi-Fi requieren su validación específica.',size=8,color='muted',wraplength=610,justify='left').pack(anchor='w')
