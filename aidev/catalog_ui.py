"""Responsive searchable lists shared by local inventories."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from .i18n import resolve_language,tr
from .storage import settings


class CatalogWindow:
    def __init__(self,title,loader,details,action=None,identifier=None,notice=None):
        self.language=resolve_language(settings().get('language','auto'))
        self.text=lambda key:tr(key,self.language)
        self.root=tk.Tk();self.root.title('AI Dev — '+self.text(title));self.root.geometry('820x580')
        self.loader,self.details,self.action=loader,details,action
        self.notice=notice
        self.identifier=identifier;self.entries=[];self.queue=queue.Queue();self.busy=False;self.closed=False
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        frame=ttk.Frame(self.root,padding=18);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=self.text(title),font=('Segoe UI',18,'bold')).pack(anchor='w')
        self.query=tk.StringVar()
        ttk.Label(frame,text=self.text('catalog_filter')).pack(anchor='w',pady=(10,0))
        ttk.Entry(frame,textvariable=self.query).pack(fill='x',pady=5)
        self.query.trace_add('write',lambda *_:self.filter())
        table=ttk.Frame(frame);table.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(table,columns=('name','origin'),show='headings',selectmode='browse')
        self.tree.heading('name',text=self.text('catalog_name'));self.tree.heading('origin',text=self.text('catalog_origin'))
        self.tree.column('name',width=360);self.tree.column('origin',width=340)
        scroll=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview);scroll.pack(side='right',fill='y')
        self.tree.configure(yscrollcommand=scroll.set);self.tree.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',lambda _:self.selection())
        self.detail=tk.Text(frame,height=9,wrap='word',state='disabled');self.detail.pack(fill='x',pady=10)
        self.status=tk.StringVar();ttk.Label(frame,textvariable=self.status,wraplength=760).pack(anchor='w')
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=8);self.buttons=buttons
        self.refresh_button=ttk.Button(buttons,text=self.text('reload'),command=self.refresh);self.refresh_button.pack(side='left')
        self.open_button=ttk.Button(buttons,text=self.text('catalog_open'),command=self.submit,state='disabled')
        if action:self.open_button.pack(side='right')
        self.refresh()

    def refresh(self):
        if self.busy:return
        self.busy=True;self.status.set(self.text('loading'));self.refresh_button.configure(state='disabled')
        def worker():
            try:self.queue.put((True,self.loader()))
            except Exception as error:self.queue.put((False,str(error)))
        threading.Thread(target=worker,daemon=True).start();self.root.after(80,self.poll)

    def poll(self):
        try:ok,result=self.queue.get_nowait()
        except queue.Empty:
            if not self.closed:self.root.after(80,self.poll)
            return
        if self.closed:return
        self.busy=False;self.refresh_button.configure(state='normal')
        if ok:
            self.entries=result;self.filter();self.status.set(self.text('catalog_count').format(count=len(result))+(('\n'+self.notice()) if self.notice else ''))
            if self.identifier and not any(e['id']==self.identifier for e in result):self.status.set(self.text('catalog_removed'))
        else:self.status.set(result)

    def filter(self):
        self.tree.delete(*self.tree.get_children())
        for e in self.entries:
            origin=e.get('host',e.get('category',''))
            if self.query.get().casefold() not in (e['name']+' '+origin).casefold():continue
            self.tree.insert('','end',iid=e['id'],values=(e['name'],origin))
            if e['id']==self.identifier:self.tree.selection_set(e['id']);self.tree.see(e['id'])
        self.selection()

    def selection(self):
        ids=self.tree.selection();e=next((e for e in self.entries if ids and e['id']==ids[0]),None)
        self.detail.configure(state='normal');self.detail.delete('1.0','end')
        if e:self.detail.insert('1.0',self.details(e))
        self.detail.configure(state='disabled');self.open_button.configure(state='normal' if e else 'disabled')

    def submit(self):
        ids=self.tree.selection()
        if ids and self.action:
            try:self.action(ids[0])
            except Exception as error:messagebox.showerror(self.text('error'),str(error),parent=self.root)

    def close(self):self.closed=True;self.root.destroy()

    def run(self):self.root.mainloop()
