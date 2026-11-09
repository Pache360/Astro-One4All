"""Manual focus aid from finite captures, without a live video buffer."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from .focus import measure
from .capture_service import capture_one

def focus_page(app):
    if not hasattr(app,'focus_state'):
        app.focus_state=tk.StringVar(value='Toma o abre un JPG con estrellas para medir el enfoque.')
        app.focus_exposure=tk.StringVar(value='2');app.focus_history=[]
    outer,body=app.card(app.content,'Una estrella más pequeña, un mejor enfoque.','ASISTENTE DE ENFOQUE MANUAL')
    outer.pack(fill='x')
    app.label(body,'Ajusta físicamente el enfoque del lente y vuelve a medir. Usa siempre el mismo campo, focal e ISO.\nEl asistente descarta estrellas saturadas y compara el radio de media luz (HFR).',justify='left',wraplength=730).pack(anchor='w',pady=(0,14))
    row=app.frame(body,'card');row.pack(fill='x')
    app.label(row,'Exposición / s',size=9,color='muted').pack(side='left');ttk.Entry(row,textvariable=app.focus_exposure,width=6).pack(side='left',padx=8)
    app.button(row,'Capturar y medir',lambda:capture(app),primary=True).pack(side='left')
    app.button(row,'Medir último JPG',lambda:analyze(app)).pack(side='left',padx=8)
    app.button(row,'Abrir JPG',app.open_jpeg).pack(side='left')
    app.label(body,variable=app.focus_state,size=11,color='accent',justify='left').pack(anchor='w',pady=(15,0))
    outer,plot=app.card(app.content,'Historial de enfoque','MENOR HFR SUELE SER MEJOR')
    outer.pack(fill='both',expand=True,pady=(14,0))
    app.focus_canvas=tk.Canvas(plot,height=170,bg=app.colors['preview'],highlightthickness=0);app.focus_canvas.pack(fill='both',expand=True)
    app.focus_canvas.bind('<Configure>',lambda e:draw(app))
    app.button(plot,'Limpiar comparación',lambda:reset(app)).pack(anchor='e',pady=10)
    app.label(plot,'No requiere enfocador motorizado. El HFR de JPG es orientativo y depende del seeing y del muestreo.',size=9,color='muted',wraplength=720,justify='left').pack(anchor='w')
    app.activity();draw(app)
def result(app,value):
    signature=(value['preview_width'],value['preview_height'],value['scale'])
    if app.focus_history and app.focus_history[-1]['signature']!=signature:
        app.focus_history=[];app.write('Cambió la escala del JPG; se reinició la comparación de enfoque.')
    value['signature']=signature;app.focus_history.append(value);app.focus_history=app.focus_history[-60:]
    app.focus_state.set(f"HFR {value['hfr_original_px']:.2f} píxeles del JPG original · {value['stars']} estrellas\nMínimo de esta comparación: {min(v['hfr_original_px'] for v in app.focus_history):.2f} px")
    draw(app)
def capture(app):
    try:
        exposure=float(app.focus_exposure.get())
        if not .001<=exposure<=30: raise ValueError('Prueba una exposición de 0.001 a 30 segundos para enfocar.')
    except ValueError as exc: app.write(str(exc));return
    def operation():
        shot=capture_one(Path.home()/'.cache/astroall/jpg',exposure,None,app.stop)
        app.post(lambda:setattr(app,'preview_path',shot['jpeg']))
        return measure(shot['jpeg'])
    app.task('Midiendo estrellas…',operation,lambda value:result(app,value))
def analyze(app):
    if not app.preview_path: app.write('Abre o captura primero un JPG.');return
    path=app.preview_path;app.task('Midiendo estrellas del JPG…',lambda:measure(path),lambda value:result(app,value))
def reset(app): app.focus_history=[];app.focus_state.set('Comparación reiniciada.');draw(app)
def draw(app):
    c=getattr(app,'focus_canvas',None)
    if not c or not c.winfo_exists(): return
    c.configure(bg=app.colors['preview']);c.delete('all');w=max(100,c.winfo_width());h=max(100,c.winfo_height());history=app.focus_history
    if not history: c.create_text(w/2,h/2,text='Tus mediciones aparecerán aquí.',fill=app.colors['muted']);return
    values=[v['hfr_original_px'] for v in history];lo=max(0,min(values)*.8);hi=max(lo+1,max(values)*1.1);coords=[]
    for i,value in enumerate(values):
        x=40+i/max(1,len(values)-1)*(w-70);y=h-30-(value-lo)/(hi-lo)*(h-60);coords.extend((x,y));c.create_oval(x-4,y-4,x+4,y+4,fill=app.colors['accent'],outline='')
    if len(values)>1: c.create_line(*coords,fill=app.colors['accent'],width=2)
    c.create_text(14,12,text=f'{hi:.1f} px',anchor='nw',fill=app.colors['muted']);c.create_text(14,h-12,text=f'{lo:.1f} px',anchor='sw',fill=app.colors['muted'])
