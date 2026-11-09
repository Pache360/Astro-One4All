"""Identify an external webcam by unplug/replug; display one confirmed image."""
import tkinter as tk
from tkinter import ttk
from .guide_camera import video_devices,usb_difference,diagnostic

def identify_usb(app,found):
    window=tk.Toplevel(app.root);window.title('Identificar mi webcam USB');window.geometry('620x250');window.transient(app.root)
    text=tk.StringVar(value='Deja conectada la webcam USB. Pulsa Registrar cámaras.\nDespués te pediremos desconectar SOLO la webcam, sin retirar el hub ni la microSD.')
    ttk.Label(window,textvariable=text,wraplength=570,justify='left',padding=18).pack(fill='x')
    stage={'step':0};button=ttk.Button(window,text='Registrar cámaras');button.pack(pady=12)
    def next_step():
        step=stage['step']
        def done(devices):
            if not window.winfo_exists(): return
            if step==0:
                stage.update(before=devices,step=1)
                text.set('Desconecta SOLO la webcam USB.\nDeja conectados el hub y la microSD. Pulsa Detectar retirada.');button.configure(text='Detectar retirada')
            elif step==1:
                try: removed=usb_difference(stage['before'],devices)
                except RuntimeError as exc: text.set(str(exc));return
                stage.update(removed=removed,step=2)
                text.set('Cámara identificada: '+removed['name']+'\nVuelve a conectarla y pulsa Encontrar USB.');button.configure(text='Encontrar USB')
            else:
                removed=stage['removed']
                matches=[d for d in devices if d['path']==removed['path'] and d['name']==removed['name']]
                if len(matches)!=1: text.set('Aún no aparece la misma webcam. Conéctala al mismo puerto y vuelve a pulsar Encontrar USB.');return
                selected=matches[0];selected.update(role='external_confirmed',label='USB identificada — '+selected['name']+' · '+selected['node'].rsplit('/',1)[-1])
                diagnostic(stage='usb_identified',confirmed_usb={k:selected[k] for k in ('path','name','bus')})
                found(devices,selected);window.destroy()
                app.write('USB identificada por desconexión: '+selected['name']+'. Ya está seleccionada.')
        app.task('Identificando webcam USB…',video_devices,done)
    button.configure(command=next_step)

def show_preview(app,result):
    from PIL import Image,ImageTk
    image=Image.open(result['jpeg']);image.load()
    if app.night:
        red=image.convert('L');zero=Image.new('L',red.size,0);image=Image.merge('RGB',(red,zero,zero))
    window=tk.Toplevel(app.root);window.title('Imagen guía — '+result['name']);window.configure(bg=app.colors['card'])
    photo=ImageTk.PhotoImage(image);label=tk.Label(window,image=photo,bg=app.colors['card']);label.image=photo;label.pack(padx=10,pady=10)
    tk.Label(window,text=f"{result['name']} · {result['width']} × {result['height']}\nComprueba que la imagen corresponde a la webcam USB.",
             bg=app.colors['card'],fg=app.colors['text'],wraplength=600).pack(padx=12,pady=(0,12))
