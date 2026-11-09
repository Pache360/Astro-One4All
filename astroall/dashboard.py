"""Lightweight observatory desktop with real device tasks and JPEG preview."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import random
import sys
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .camera import open_camera
from .controls import clock_window, mount_window, optics_window
from .doctor import report
from .night import NightScreen
from .solve import drift_report, solve_jpeg
from .timekeeping import clock_snapshot, load_settings
from . import __version__

DAY = dict(bg='#0b101b', sidebar='#0e1421', card='#131c2c', field='#192438',
           border='#243047', text='#e7edf6', muted='#8b9bb4', accent='#afa2ff',
           primary='#8270e7', success='#72d9bf', danger='#ed929b', preview='#090e18')
NIGHT = dict(bg='#080000', sidebar='#0d0101', card='#170303', field='#230505',
             border='#40100d', text='#d76b57', muted='#9b4438', accent='#ed7159',
             primary='#792b23', success='#d46b55', danger='#ef7963', preview='#070000')


class Dashboard:
    def __init__(self, root):
        self.root, self.colors = root, DAY.copy()
        self.night, self.busy, self.reference = False, False, None
        self.screen = NightScreen()
        self.messages, self.stop = queue.Queue(), threading.Event()
        self.painted, self.nav = [], {}
        self.current_page, self.preview_path, self.preview_photo = 'session', None, None
        self.plan_targets=[];self.selected_target=None
        self.detected_camera = False
        self.diagnostic = None
        self.last_task_error = None
        self.last_camera_info = None
        self.completed = 0
        self.requested = 1
        self.count, self.delay = tk.StringVar(value='1'), tk.StringVar(value='3')
        self.width = tk.StringVar(value='25.1427')
        self.status = tk.StringVar(value='Todo listo para comprobar tu equipo')
        self.mount_badge=tk.StringVar(value='Montura: sin conectar')
        self.clock_text = tk.StringVar()
        self.progress_text = tk.StringVar(value='Sin capturas en esta sesión')
        self.font = 'Segoe UI' if root.tk.call('tk','windowingsystem') == 'win32' else 'DejaVu Sans'
        self.buttons=[]
        root.title('Astro One4All · Observatorio portátil')
        root.geometry('1120x740')
        root.minsize(960, 640)
        root.configure(bg=self.colors['bg'])
        if os.name=='posix' and Path('/etc/astroall-live').exists():
            root.attributes('-fullscreen',True)
        root.option_add('*Font', (self.font, 10))
        self.style = ttk.Style(root)
        self.style.theme_use('clam')
        self.configure_styles()
        shell = self.frame(root, 'bg')
        shell.pack(fill='both', expand=True)
        self.sidebar = self.frame(shell, 'sidebar', width=172)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)
        brand = self.frame(self.sidebar, 'sidebar')
        brand.pack(fill='x', padx=20, pady=(18, 16))
        self.logo = tk.Canvas(brand, width=48, height=48, bg=self.colors['sidebar'], highlightthickness=0)
        self.logo.pack(anchor='w')
        self.label(brand, 'ASTRO', size=19, bold=True).pack(anchor='w', pady=(10, 0))
        self.label(brand, 'ONE4ALL', size=10, color='accent', bold=True).pack(anchor='w')
        self.label(self.sidebar, 'OBSERVATORIO', size=8, color='muted').pack(anchor='w', padx=20, pady=(0, 12))
        for key, name in [('session','Sesión de fotos'), ('atlas','Atlas del cielo'), ('mount','Montura'), ('guide','Autoguiado'), ('focus','Enfoque'), ('polar','Alineación polar'), ('system','Equipo y sistema')]:
            from .ui_widgets import RoundedButton
            b=RoundedButton(self.sidebar,name,lambda k=key:self.show(k),self,navigation=True,width=156)
            self.buttons.append(b)
            b.pack(fill='x', padx=8, pady=2)
            self.nav[key] = b
        bottom = self.frame(self.sidebar, 'sidebar')
        bottom.pack(side='bottom', fill='x', padx=18, pady=17)
        self.button(bottom, 'Modo noche · F8', self.toggle_night).pack(fill='x', pady=(0, 14))
        self.label(bottom, 'OBSERVATORIO', size=8, color='muted').pack(anchor='w')
        self.label(bottom, 'Modo portátil', size=10).pack(anchor='w', pady=(6, 2))
        self.label(bottom, 'Desde 2 GB de RAM', size=9, color='muted').pack(anchor='w')
        self.label(bottom, 'Prueba Live '+__version__, size=9, color='muted').pack(anchor='w', pady=(14, 0))
        main = self.frame(shell, 'bg')
        main.pack(side='left', fill='both', expand=True, padx=24, pady=16)
        top = self.frame(main, 'bg')
        top.pack(fill='x', pady=(0, 18))
        self.heading = self.label(top, '', size=21, bold=True)
        self.heading.pack(side='left')
        self.label(top, variable=self.clock_text, size=9, color='muted', justify='right').pack(side='right')
        from .preferences_ui import settings_window
        self.button(top,'Configuración',lambda:settings_window(self)).pack(side='right',padx=(8,12))
        self.content = self.frame(main, 'bg')
        self.content.pack(fill='both', expand=True)
        footer = self.frame(main, 'bg')
        footer.pack(fill='x', pady=(12, 0))
        self.label(footer, '●', color='accent', size=9).pack(side='left')
        self.label(footer, variable=self.status, size=9, color='muted').pack(side='left', padx=8)
        self.label(footer, variable=self.mount_badge, size=8, color='accent').pack(side='right')
        self.log_lines = ['Bienvenido. Comienza con una foto corta para comprobar RAW + JPG en la SD.']
        self.root.report_callback_exception=self.report_ui_error
        self.show('session')
        self.draw_logo()
        root.bind('<F8>', lambda event:self.toggle_night())
        root.bind('<F11>', lambda event:root.attributes('-fullscreen',not root.attributes('-fullscreen')))
        root.bind('<Escape>', lambda event:root.attributes('-fullscreen',False))
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(100,self.poll)
        root.after(100,self.tick)
        from .preferences import load as preferences
        if preferences()['night_start']:root.after(150,self.toggle_night)

    def frame(self, parent, role='bg', **kwargs):
        widget = tk.Frame(parent, bg=self.colors[role], **kwargs)
        self.painted.append((widget, role, None))
        return widget

    def label(self, parent, text='', size=10, color='text', bold=False, variable=None, **kwargs):
        widget = tk.Label(parent, text=text, textvariable=variable, bg=parent.cget('bg'),
                          fg=self.colors[color], font=(self.font,size,'bold' if bold else 'normal'), bd=0, **kwargs)
        self.painted.append((widget, None, color))
        return widget

    def button(self, parent, text, command, primary=False, danger=False):
        from .ui_widgets import RoundedButton
        button=RoundedButton(parent,text,command,self,primary,danger);self.buttons.append(button);return button

    def card(self, parent, title, eyebrow=None):
        outer = self.frame(parent,'card',highlightbackground=self.colors['border'],highlightthickness=1)
        inside = self.frame(outer,'card')
        inside.pack(fill='both',expand=True,padx=14,pady=8)
        if eyebrow:
            self.label(inside,eyebrow,size=8,color='accent',bold=True).pack(anchor='w',pady=(0,5))
        if title:
            self.label(inside,title,size=12,bold=True).pack(anchor='w',pady=(0,8))
        return outer,inside

    def configure_styles(self):
        c=self.colors
        self.style.configure('.',font=(self.font,10),background=c['bg'],foreground=c['text'])
        self.style.configure('TFrame',background=c['bg'])
        self.style.configure('TLabel',background=c['bg'],foreground=c['text'])
        self.style.configure('TCheckbutton',background=c['bg'],foreground=c['text'])
        self.style.configure('Treeview',background=c['field'],fieldbackground=c['field'],foreground=c['text'],rowheight=23,bordercolor=c['border'])
        self.style.configure('Treeview.Heading',background=c['card'],foreground=c['muted'],relief='flat')
        self.style.map('Treeview',background=[('selected',c['primary'])],foreground=[('selected',c['text'])])
        self.style.configure('TNotebook',background=c['card'],borderwidth=0)
        self.style.configure('TNotebook.Tab',background=c['field'],foreground=c['muted'],padding=(9,5),borderwidth=0)
        self.style.map('TNotebook.Tab',background=[('selected',c['primary'])],foreground=[('selected',c['text'])])
        self.style.configure('TButton',background=c['field'],foreground=c['text'],borderwidth=0,padding=(10,5),relief='flat')
        self.style.map('TButton',background=[('active',c['border']),('disabled',c['card'])],foreground=[('disabled',c['muted'])])
        self.style.configure('Primary.TButton',background=c['primary'],foreground=c['text'],font=(self.font,10,'bold'))
        self.style.map('Primary.TButton',background=[('active',c['primary']),('disabled',c['card'])])
        self.style.configure('Danger.TButton',foreground=c['danger'])
        self.style.configure('TEntry',fieldbackground=c['field'],foreground=c['text'],insertcolor=c['text'],bordercolor=c['border'],padding=4)
        self.style.configure('TCombobox',fieldbackground=c['field'],background=c['field'],foreground=c['text'],padding=4)
        self.style.map('TCombobox',fieldbackground=[('readonly',c['field'])],foreground=[('readonly',c['text'])])
        self.style.configure('Horizontal.TProgressbar',background=c['accent'],troughcolor=c['field'],borderwidth=0,lightcolor=c['accent'],darkcolor=c['accent'])
        self.root.option_add('*TCombobox*Listbox.background',c['field'])
        self.root.option_add('*TCombobox*Listbox.foreground',c['text'])

    def show(self,page):
        if self.current_page=='polar':
            from .polar_ui import pause
            pause(self)
        if hasattr(self,'hand'): self.hand.release()
        self.current_page=page
        for child in self.content.winfo_children(): child.destroy()
        self.painted=[item for item in self.painted if item[0].winfo_exists()]
        self.buttons=[button for button in self.buttons if button.winfo_exists()]
        self.heading.configure(text={'session':'Tu noche, bajo control.','atlas':'Explora tu próximo encuadre.','mount':'El cielo, en tus manos.','guide':'Cada estrella, en su lugar.','focus':'Encuentra la nitidez.','polar':'Encuentra el polo.','system':'Tu equipo, a tu manera.'}[page])
        for key,button in self.nav.items():
            button.set_selected(key==page)
        if page=='session':
            from .session_ui import session_page
            session_page(self)
        elif page=='atlas':
            from .atlas_ui import atlas_page
            atlas_page(self)
        elif page=='mount':
            from .mount_ui import mount_page
            mount_page(self)
        elif page=='guide':
            from .guide_ui import guide_page
            guide_page(self)
        elif page=='focus':
            from .focus_ui import focus_page
            focus_page(self)
        elif page=='polar': self.polar_page()
        else: self.system_page()

    def session_page(self):
        states=self.frame(self.content)
        states.pack(fill='x',pady=(0,14))
        for i,(title,value,note) in enumerate([('CÁMARA','Canon EOS R50','Detectada · conexión liberada' if self.detected_camera else 'Sin comprobar'),
                                              ('MONTURA','OpenAstroTracker','USB · 19200 baudios'),('ALMACENAMIENTO','RAW en la Canon','SD 128 GB · JPG ligero al PC')]):
            outer,inner=self.card(states,'',title)
            outer.pack(side='left',fill='x',expand=True,padx=(0,10 if i<2 else 0))
            self.label(inner,value,size=12,bold=True).pack(anchor='w')
            self.label(inner,note,size=8,color='muted').pack(anchor='w',pady=(7,0))
        work=self.frame(self.content)
        work.pack(fill='both',expand=True)
        view,inner=self.card(work,'Última imagen','ENCUADRE')
        view.pack(side='left',fill='both',expand=True,padx=(0,14))
        self.preview=tk.Canvas(inner,bg=self.colors['preview'],highlightthickness=0,height=220)
        self.preview.pack(fill='both',expand=True)
        self.preview.bind('<Configure>',lambda event:self.render_preview())
        preview_actions=self.frame(inner,'card')
        preview_actions.pack(fill='x',pady=(12,0))
        self.button(preview_actions,'Abrir JPG',self.open_jpeg).pack(side='left')
        self.button(preview_actions,'Nueva referencia',self.reset_reference).pack(side='left',padx=7)
        self.button(preview_actions,'Resolver campo',self.solve_current).pack(side='right')
        right=self.frame(work)
        right.pack(side='right',fill='y')
        outer,settings=self.card(right,'Una toma a la vez.','SECUENCIA')
        outer.pack(fill='x')
        self.label(settings,'Exposición e ISO en la cámara',size=9,color='muted').pack(anchor='w',pady=(0,12))
        inputs=self.frame(settings,'card')
        inputs.pack(fill='x')
        for title,variable in [('Fotos',self.count),('Pausa / s',self.delay)]:
            column=self.frame(inputs,'card')
            column.pack(side='left',fill='x',expand=True,padx=(0,10))
            self.label(column,title,size=9,color='muted').pack(anchor='w',pady=(0,6))
            ttk.Entry(column,textvariable=variable,width=8).pack(fill='x')
        self.label(settings,'M · RAW + JPG Med · hasta 30 s',size=8,color='muted').pack(anchor='w',pady=(12,12))
        self.capture_button=self.button(settings,'Iniciar captura',self.start_capture,primary=True)
        self.capture_button.pack(fill='x')
        if self.busy: self.capture_button.state(['disabled'])
        self.button(settings,'Detener después de esta toma',self.stop.set).pack(fill='x',pady=(8,0))
        self.label(settings,variable=self.progress_text,size=8,color='muted').pack(anchor='w',pady=(12,4))
        self.progress=ttk.Progressbar(settings,maximum=100,value=100*self.completed/max(1,self.requested))
        self.progress.pack(fill='x')
        self.button(settings,'Elegir lente / calcular campo',lambda:optics_window(self.root,self.width,self.write)).pack(fill='x',pady=(14,0))
        self.label(settings,'18–45 · 50 · 55–250 · 10 mm',size=8,color='muted').pack(anchor='w',pady=(8,0))
        self.activity()

    def activity(self):
        outer,inner=self.card(self.content,'')
        outer.pack(fill='x',pady=(14,0))
        header=self.frame(inner,'card')
        header.pack(fill='x')
        self.latest=self.label(header,self.log_lines[-1][:84],size=9,anchor='w',justify='left')
        self.latest.pack(side='left',fill='x',expand=True)
        self.button(header,'Ver registro',self.show_log).pack(side='right')

    def mount_page(self):
        outer,inside=self.card(self.content,'Tu OAT, con su configuración intacta.','MEGA 2560 + RAMPS 1.4')
        outer.pack(fill='x')
        self.label(inside,'NEMA 17 · TMC2209 standalone 1/64 · poleas GT2 16T',color='muted').pack(anchor='w',pady=(0,12))
        self.label(inside,'Control USB a 19200 baudios. El mando LCD conserva su funcionamiento autónomo.',size=10).pack(anchor='w')
        self.label(inside,'La versión instalada se consulta al equipo; no se infiere del HEX preparado.',size=9,color='muted').pack(anchor='w',pady=(8,18))
        self.button(inside,'Abrir control de montura',lambda:mount_window(self.root,self.task,self.write,self.post),primary=True).pack(anchor='w')
        self.label(inside,'Identificación, conexión, coordenadas de fecha, GoTo y parada.',size=9,color='muted').pack(anchor='w',pady=(14,0))
        self.activity()

    def polar_page(self):
        from .polar_ui import page
        page(self)

    def system_page(self):
        from .equipment_ui import equipment_page
        equipment_page(self)

    def system_diagnostics_legacy(self):
        outer,inside=self.card(self.content,'Lista para una primera prueba.','EQUIPO Y SISTEMA')
        outer.pack(fill='x')
        self.label(inside,'Comprueba controladores, cámara y almacenamiento antes de la primera toma.',color='muted').pack(anchor='w',pady=(0,16))
        buttons=self.frame(inside,'card')
        buttons.pack(fill='x')
        self.button(buttons,'Comprobar equipo',lambda:self.task('Comprobando equipo…',report,self.on_report),primary=True).pack(side='left',padx=(0,10))
        self.button(buttons,'Detectar cámara',lambda:self.task('Consultando cámara…',self.camera_info,self.on_camera)).pack(side='left')
        tests=self.frame(inside,'card');tests.pack(fill='x',pady=(12,0))
        self.button(tests,'Prueba foto · 1 s',lambda:self.test_camera(False)).pack(side='left',padx=(0,10))
        self.button(tests,'Prueba Bulb · 3 s',lambda:self.test_camera(True)).pack(side='left')
        self.label(inside,'Cámara en M, RAW + JPG y enfoque manual. Cada prueba toma una foto real en la SD.',size=9,color='muted',wraplength=700,justify='left').pack(anchor='w',pady=(10,0))
        more,body=self.card(self.content,'A tu manera.','PREFERENCIAS')
        more.pack(fill='x',pady=(14,0))
        from .atlas_ui import site_window
        self.button(body,'Ubicación, reloj y zona para viajes',lambda:site_window(self)).pack(anchor='w',pady=(0,10))
        self.button(body,'Guardar diagnóstico',self.export_diagnostic).pack(anchor='w')
        self.button(body,'Apagar o reiniciar',self.power_dialog).pack(anchor='w',pady=(10,0))
        self.label(body,'La microSD de 32 GB contiene el sistema. Los originales quedan en la SD de la Canon.',size=9,color='muted',wraplength=700,justify='left').pack(anchor='w',pady=(16,0))
        self.activity()

    def power_dialog(self):
        if self.busy:
            messagebox.showinfo('Tarea en curso','Detén la captura y espera su cierre antes de apagar.',parent=self.root);return
        import subprocess
        path=Path('/usr/bin/lxsession-logout')
        if not path.is_file():
            messagebox.showerror('Apagado','Esta opción requiere Astro One4All Live. En Linux puedes apagar con sudo systemctl poweroff.',parent=self.root);return
        subprocess.Popen([str(path)])

    def camera_info(self):
        from .camera_diagnostic import CaptureReport
        with open_camera(CaptureReport(probe_only=True,photos_requested=0)) as camera: return camera.inspect()

    def on_camera(self,value):
        self.detected_camera=True
        self.last_camera_info=value
        self.write('Cámara detectada: '+value.get('model','sin identificar')+'. '+value.get('adapter','Perfil dedicado Canon R50 · enfoque manual y guiado opcional.'))
        self.write(value)

    def test_camera(self,bulb):
        if self.busy: self.write('Espera a que termine la tarea en curso.');return
        label='Bulb de 3 s' if bulb else 'exposición fija de 1 s'
        if not messagebox.askyesno('Probar captura',f'Se tomará una foto real con {label}.\nCámara en M · RAW + JPG · enfoque manual.\n¿Iniciar prueba?',parent=self.root): return
        from .capture_service import capture_one
        def done(result):
            self.preview_path=result['jpeg']
            self.write(f"Prueba confirmada: {result['sd_raw']} y {result['sd_jpeg']} en SD; solo JPG recibido. Exposición: {result['exposure_seconds']:.2f} s.")
            self.render_preview()
        self.task('Probando '+label+'…',lambda:capture_one(Path.home()/'.cache/astroall/jpg',3 if bulb else 1,stop=self.stop,force_bulb=bulb),done)

    def on_report(self,value):
        self.diagnostic=value
        available=sum(bool(v) for v in value['tools'].values())
        self.write(f'Diagnóstico: {available} herramientas disponibles. '+(' · '.join(value['warnings']) or 'Sin advertencias de preparación.'))

    def task(self,label,function,callback=None):
        if self.busy:
            self.write('Hay una tarea en curso. Espera su resultado.')
            return False
        self.busy=True
        self.last_task_error=None
        self.stop.clear()
        self.status.set(label)
        if self.current_page=='session': self.capture_button.state(['disabled'])
        def worker():
            try:
                value=function()
                self.messages.put(('result',(callback,value)))
            except Exception as exc: self.messages.put(('error',str(exc)))
            finally: self.messages.put(('done',None))
        threading.Thread(target=worker,daemon=True).start()
        return True

    def post(self,function): self.messages.put(('ui',function))

    def start_capture(self):
        from .__main__ import capture_sequence
        try: count,delay=int(self.count.get()),float(self.delay.get())
        except ValueError:
            self.write('Indica una cantidad entera de fotos y una pausa numérica.')
            return
        self.completed=0
        self.requested=max(1,count)
        self.task('Capturando a SD…',lambda:capture_sequence(count,delay,Path.home()/'.cache/astroall/jpg',
                  lambda value:self.messages.put(('shot',value)),self.stop))

    def open_jpeg(self):
        path=filedialog.askopenfilename(title='Abrir un JPG',filetypes=[('JPEG','*.jpg *.jpeg *.JPG')])
        if path:
            self.preview_path=path
            self.render_preview()
            self.write('JPG abierto: '+Path(path).name)

    def solve_current(self):
        if not self.preview_path:
            self.write('Abre un JPG o captura una foto antes de resolver el campo.')
            return
        try: field=float(self.width.get())
        except ValueError:
            self.write('Selecciona lente y focal antes de resolver.')
            return
        path=self.preview_path
        def solved(position):
            if self.reference is None:
                self.reference=position
                self.write(f'Referencia: AR {position.ra_deg:.5f}°, DEC {position.dec_deg:.5f}° (ICRS).')
            else: self.write(drift_report(self.reference,position))
        self.task('Resolviendo campo…',lambda:self.solve(path,field),solved)

    def reset_reference(self):
        self.reference=None
        self.write('La próxima imagen resuelta será la nueva referencia de encuadre.')

    def solve(self,path,field):
        return solve_jpeg(path,field,[Path.home()/'astroall-data/indexes','/usr/share/astrometry'])

    def open_polar(self):
        self.show('polar')

    def write(self,value):
        text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)
        self.log_lines.append(datetime.now().strftime('%H:%M')+'  '+text)
        self.log_lines=self.log_lines[-120:]
        if hasattr(self,'latest') and self.latest.winfo_exists(): self.latest.configure(text=text.replace('\n',' ')[:84])

    def show_log(self):
        dialog=tk.Toplevel(self.root)
        dialog.title('Astro One4All · Registro de sesión')
        dialog.geometry('780x430')
        text=tk.Text(dialog,bg=self.colors['card'],fg=self.colors['text'],relief='flat',wrap='word',font=(self.font,10),padx=16,pady=16)
        text.pack(fill='both',expand=True)
        text.insert('end','\n\n'.join(self.log_lines))
        text.configure(state='disabled')
        self.painted.append((text,'card','text'))

    def export_diagnostic(self):
        from .camera_diagnostic import read_diagnostic
        from .mount_service import profile as mount_profile
        from .guide_camera import profile as guide_profile
        path=filedialog.asksaveasfilename(title='Guardar diagnóstico',defaultextension='.json',initialfile='astroall-diagnostico.json')
        if path:
            from .awake import status as power_status
            value={'application_version':__version__,'power':power_status(),'equipment':self.diagnostic,'camera':self.last_camera_info,
                   'last_capture':read_diagnostic(),'last_error':self.last_task_error,'activity':self.log_lines,
                   'mount_profile':mount_profile(),'guide_camera':guide_profile(),
                   'current_page':self.current_page,
                   'mount_live':{'status':self.mount_badge.get(),'snapshot':getattr(self,'mount_snapshot',{}),
                                 'observed_utc':getattr(self,'mount_observed_utc',None),
                                 'client_active':bool(getattr(getattr(self,'hand',None),'client',None))}}
            ui_log=Path.home()/'.local/state/astroall/ui-errors.jsonl'
            try: value['ui_errors']=[json.loads(line) for line in ui_log.read_text(encoding='utf-8').splitlines()[-10:]]
            except (OSError,ValueError): value['ui_errors']=[]
            mount_log=Path.home()/'.local/state/astroall/mount-diagnostic.json'
            try: value['mount_connection']=json.loads(mount_log.read_text(encoding='utf-8'))
            except (OSError,ValueError): pass
            from .guide_camera import state_path
            try: value['guide_diagnostic']=json.loads(state_path().read_text(encoding='utf-8'))
            except (OSError,ValueError): pass
            if hasattr(self,'polar'):value['polar']=self.polar['session'].diagnostic()
            Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
            self.write('Diagnóstico guardado.')

    def draw_logo(self):
        from .ui_widgets import draw_mapache
        self.logo.configure(bg=self.colors['sidebar']);draw_mapache(self.logo,self.colors)

    def render_preview(self):
        if not hasattr(self,'preview') or not self.preview.winfo_exists(): return
        canvas=self.preview
        w,h=max(100,canvas.winfo_width()),max(100,canvas.winfo_height())
        canvas.configure(bg=self.colors['preview'])
        canvas.delete('all')
        if self.preview_path:
            try:
                from PIL import Image,ImageTk,ImageOps
                with Image.open(self.preview_path) as image:
                    if image.width*image.height>30_000_000: raise ValueError('El JPG supera el tamaño de vista previa.')
                    image.draft('RGB',(w,h))
                    image.thumbnail((w,h))
                    image=image.convert('RGB')
                    if self.night: image=ImageOps.colorize(ImageOps.grayscale(image),'#070000','#b65443')
                    self.preview_photo=ImageTk.PhotoImage(image)
                canvas.create_image(w/2,h/2,image=self.preview_photo)
                return
            except Exception as exc:
                self.preview_path=None
                self.write('No se pudo mostrar el JPG: '+str(exc))
        randomizer=random.Random(48)
        for _ in range(34):
            x,y=randomizer.randrange(max(1,w)),randomizer.randrange(max(1,h))
            canvas.create_oval(x,y,x+1,y+1,fill=self.colors['border'],outline='')
        cx,cy=w/2,h/2-25
        canvas.create_oval(cx-25,cy-25,cx+25,cy+25,outline=self.colors['border'],width=2)
        canvas.create_line(cx-36,cy,cx-15,cy,fill=self.colors['muted'])
        canvas.create_line(cx+15,cy,cx+36,cy,fill=self.colors['muted'])
        canvas.create_line(cx,cy-36,cx,cy-15,fill=self.colors['muted'])
        canvas.create_line(cx,cy+15,cx,cy+36,fill=self.colors['muted'])
        canvas.create_text(cx,cy+62,text='Aquí empieza tu próxima imagen.',fill=self.colors['muted'],font=(self.font,11))
        canvas.create_text(cx,cy+85,text='Vista del último JPG · sin imagen todavía',fill=self.colors['muted'],font=(self.font,8))

    def toggle_night(self):
        self.night=not self.night
        self.colors=(NIGHT if self.night else DAY).copy()
        self.root.configure(bg=self.colors['bg'])
        self.configure_styles()
        alive=[]
        for widget,background,foreground in self.painted:
            if not widget.winfo_exists(): continue
            if background: widget.configure(bg=self.colors[background])
            elif isinstance(widget,tk.Label): widget.configure(bg=widget.master.cget('bg'))
            if foreground: widget.configure(fg=self.colors[foreground])
            if isinstance(widget,tk.Frame) and int(widget.cget('highlightthickness')):
                widget.configure(highlightbackground=self.colors['border'])
            alive.append((widget,background,foreground))
        self.painted=alive
        for button in self.buttons:
            if button.winfo_exists():button.redraw()
        self.draw_logo()
        self.show(self.current_page)
        if self.night:
            try:
                self.screen.enable()
                self.write('Modo noche: rojo global activo. F8 restaura los colores.')
            except Exception:
                self.write('Modo noche rojo de la app activo. El rojo global requiere Linux/X11 compatible.')
        else:
            self.screen.restore()
            self.write('Colores normales restaurados.')

    def poll(self):
        # Views are replaced while equipment and capture workers keep running.
        # A late callback from an old view must not stop the event pump.
        try:
            while True:
                kind,value=self.messages.get_nowait()
                try: self.handle_message(kind,value)
                except Exception: self.report_ui_error(*sys.exc_info())
        except queue.Empty: pass
        if self.root.winfo_exists(): self.root.after(100,self.poll)

    def report_ui_error(self,kind,value,tb):
        record={'utc':datetime.now(timezone.utc).isoformat(),'page':self.current_page,
                'type':kind.__name__,'error':str(value),'traceback':''.join(traceback.format_exception(kind,value,tb))[-16000:]}
        try:
            path=Path.home()/'.local/state/astroall/ui-errors.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists() and path.stat().st_size>131072: path.replace(path.with_suffix('.previous.jsonl'))
            with path.open('a',encoding='utf-8') as stream: stream.write(json.dumps(record,ensure_ascii=False)+'\n')
        except OSError: pass
        self.write('Error de interfaz en '+self.current_page+': '+str(value))

    def handle_message(self,kind,value):
        if kind=='ui': value()
        elif kind=='result':
            callback,result=value
            if callback and result is not None: callback(result)
            elif result is not None: self.write(result)
        elif kind=='error':
            self.last_task_error=value
            self.write('No se completó la tarea: '+value)
            self.status.set('No se completó la tarea · ver actividad')
            messagebox.showerror('No se completó la tarea',value+'\n\nPuedes guardar los detalles desde Equipo y sistema → Guardar diagnóstico.',parent=self.root)
        elif kind=='shot':
            self.completed=value['shot']
            self.preview_path=value['jpeg']
            self.progress_text.set(f"{value['shot']} de {value['total']} fotos · JPG recibido")
            if self.current_page=='session':
                self.progress.configure(value=100*value['shot']/value['total'])
                self.render_preview()
            self.write(f"Foto {value['shot']}: {value['sd_raw']} y {value['sd_jpeg']} en SD. Solo JPG descargado.")
        elif kind=='done':
            self.busy=False
            if not self.last_task_error: self.status.set('Tarea finalizada · consulta la actividad')
            if self.current_page=='session': self.capture_button.state(['!disabled'])

    def tick(self):
        try:
            # The header only needs civil time; don't calculate sidereal time every second.
            settings=load_settings()
            time=clock_snapshot(dict(settings,longitude=None))
            self.clock_text.set(time['local'][11:19]+'  LOCAL\n'+time['utc'][11:16]+' UTC · '+('OAT' if settings.get('clock_anchor') and settings.get('clock_confirmed') else 'PC'))
        except Exception: self.clock_text.set(datetime.now(timezone.utc).strftime('%H:%M UTC'))
        self.root.after(1000,self.tick)

    def close(self):
        if self.busy:
            self.stop.set()
            messagebox.showinfo('Tarea en curso','Se detendrá después de esta foto. Espera a que termine antes de cerrar.')
            return
        self.screen.restore()
        if hasattr(self,'hand'): self.hand.close()
        self.root.destroy()


def run():
    from .awake import apply as keep_awake
    try:power=keep_awake()
    except Exception as exc:power={'applied':False,'error':str(exc)}
    root=tk.Tk()
    app=Dashboard(root)
    if power.get('applied'):app.write('Pantalla siempre encendida · protección de sesión Live activa.')
    elif power.get('live'):app.write('No se confirmó la protección de pantalla. Consulta Equipo y sistema → Comprobar sistema.')
    try: root.mainloop()
    finally: app.screen.restore()
