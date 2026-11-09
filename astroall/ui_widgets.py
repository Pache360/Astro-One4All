"""Small native rounded controls: no web engine, image cache or animation loop."""
import tkinter as tk
from tkinter import font as tkfont

class RoundedButton(tk.Canvas):
    def __init__(self,parent,text,command,app,primary=False,danger=False,navigation=False,width=None):
        self.app,self.text,self.command=app,text,command
        self.primary,self.danger,self.navigation=primary,danger,navigation
        self.disabled=self.hover=self.pressed=self.selected=self.focused=False
        self.typeface=tkfont.Font(family=app.font,size=10,weight='bold' if primary else 'normal')
        super().__init__(parent,width=width or max(38,self.typeface.measure(text)+26),height=35 if navigation else 28,
                         bg=parent.cget('bg'),highlightthickness=0,bd=0,takefocus=1,cursor='hand2')
        self.bind('<Configure>',lambda e:self.redraw())
        self.bind('<Enter>',lambda e:self.change(hover=True));self.bind('<Leave>',lambda e:self.change(hover=False,pressed=False))
        self.bind('<ButtonPress-1>',self.press);self.bind('<ButtonRelease-1>',self.release)
        self.bind('<FocusIn>',lambda e:self.change(focused=True));self.bind('<FocusOut>',lambda e:self.change(focused=False,pressed=False))
        self.bind('<KeyRelease-space>',lambda e:self.invoke());self.bind('<KeyRelease-Return>',lambda e:self.invoke())
        self.redraw()

    def change(self,**values):
        for name,value in values.items():setattr(self,name,value)
        self.redraw()

    def set_selected(self,value):self.change(selected=bool(value))
    def press(self,event):
        if not self.disabled:self.focus_set();self.change(pressed=True)
    def release(self,event):
        active=self.pressed and 0<=event.x<self.winfo_width() and 0<=event.y<self.winfo_height()
        self.change(pressed=False)
        if active:self.invoke()
    def invoke(self):
        if not self.disabled and self.command:return self.command()
    def state(self,states=None):
        if states is None:return ('disabled',) if self.disabled else ()
        if 'disabled' in states:self.disabled=True
        if '!disabled' in states:self.disabled=False
        self.redraw()
    def configure(self,cnf=None,**kwargs):
        if isinstance(cnf,dict):kwargs=dict(cnf,**kwargs);cnf=None
        if 'text' in kwargs:
            self.text=kwargs.pop('text');kwargs.setdefault('width',max(38,self.typeface.measure(self.text)+26))
        if 'command' in kwargs:self.command=kwargs.pop('command')
        result=super().configure(cnf,**kwargs)
        if hasattr(self,'typeface'):self.redraw()
        return result
    config=configure

    def redraw(self):
        if not self.winfo_exists():return
        c=self.app.colors;super().configure(bg=self.master.cget('bg'))
        self.delete('all');w=max(self.winfo_width(),int(self.cget('width')));h=int(self.cget('height'));r=10
        fill=c['danger'] if self.danger else c['primary'] if self.primary else c['field']
        if self.navigation:fill=c['field'] if self.selected or self.hover else c['sidebar']
        elif self.hover and not self.disabled:fill=c['border'] if not self.primary else c['primary']
        if self.disabled:fill=c['card']
        outline=c['accent'] if self.focused and not self.disabled else c['border'] if self.hover else fill
        def rounded(x,y,right,bottom,color):
            radius=min(12,(bottom-y)/2,(right-x)/2)
            self.create_rectangle(x+radius,y,right-radius,bottom,fill=color,outline='')
            self.create_rectangle(x,y+radius,right,bottom-radius,fill=color,outline='')
            for left,top in ((x,y),(right-2*radius,y),(x,bottom-2*radius),(right-2*radius,bottom-2*radius)):
                self.create_oval(left,top,left+2*radius,top+2*radius,fill=color,outline='')
        rounded(1,1,w-1,h-1,outline)
        rounded(2,2,w-2,h-2,fill)
        foreground=c['muted'] if self.disabled else c['text'] if self.danger else c['accent'] if self.selected else c['muted'] if self.navigation else c['text']
        if self.navigation and self.selected:self.create_line(7,10,7,h-10,fill=c['accent'],width=3,capstyle='round')
        self.create_text(18 if self.navigation else w/2,h/2+(1 if self.pressed else 0),text=self.text,
                         anchor='w' if self.navigation else 'center',fill=foreground,font=self.typeface)

def draw_mapache(canvas,colors):
    """Original vector raccoon emblem; recolors with the red night palette."""
    canvas.delete('all');c=colors;scale=min(int(canvas.cget('width')),int(canvas.cget('height')))/64
    def oval(box,fill,outline='',width=1):return canvas.create_oval(*(x*scale for x in box),fill=fill,outline=outline,width=width)
    def polygon(points,fill):return canvas.create_polygon(*(x*scale for x in points),fill=fill,smooth=True,splinesteps=20)
    oval((3,3,58,58),'',c['accent'])
    oval((9,8,27,30),c['text']);oval((37,8,55,30),c['text'])
    oval((13,12,23,26),c['field']);oval((41,12,51,26),c['field'])
    polygon((32,15,51,20,58,37,47,51,32,58,17,51,6,37,13,20),c['text'])
    polygon((9,30,24,24,32,34,24,44,11,40),c['sidebar'])
    polygon((55,30,40,24,32,34,40,44,53,40),c['sidebar'])
    oval((20,31,25,36),c['accent']);oval((39,31,44,36),c['accent'])
    polygon((32,35,44,43,40,51,32,56,24,51,20,43),c['muted'])
    oval((27,40,37,47),c['sidebar'])
    canvas.create_line(32*scale,46*scale,32*scale,50*scale,fill=c['sidebar'],width=1)
    canvas.create_line(54*scale,5*scale,54*scale,15*scale,fill=c['accent'],width=2)
    canvas.create_line(49*scale,10*scale,59*scale,10*scale,fill=c['accent'],width=2)
