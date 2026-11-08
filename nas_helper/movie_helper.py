#!/usr/bin/env python3
"""Local watchlist lookup and QNAP Download Station helper (Python 3.9+)."""
import base64, csv, hashlib, html, http.client, ipaddress, json, re, ssl, threading, time, urllib.parse, urllib.request, webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from html.parser import HTMLParser

BASE = 'https://www.seedhub.cc'
MAX_PAGE = 3_000_000

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.items=[]; self.current=None
    def handle_starttag(self, tag, attrs):
        if tag!='a': return
        a=dict(attrs); href=a.get('href',''); title=a.get('title','')
        if re.fullmatch(r'/movies/\d+/?',href) and title:
            self.items.append((title,href))
        elif href.startswith('/link_start/') and 'seed_id=' in href:
            self.items.append((title or '未命名资源',href))

def parse_links(page):
    p=Links(); p.feed(page); return list(dict.fromkeys(p.items))

def parse_magnet(page):
    direct=re.search(r'magnet:\?xt=urn:btih:[0-9a-zA-Z]{32,40}[^\s"\'<>]*',html.unescape(page),re.I)
    if direct: return direct.group(0)
    for encoded in re.findall(r'\b(?:const|let|var)\s+data\s*=\s*["\']([A-Za-z0-9+/=]+)["\']',page):
        try: value=base64.b64decode(encoded,validate=True).decode('utf-8')
        except (ValueError,UnicodeError): continue
        if re.match(r'^magnet:\?xt=urn:btih:[0-9a-zA-Z]{32,40}(?:&|$)',value,re.I): return value
    raise ValueError('页面没有可识别的磁力链接')

def fetch(path):
    if not path.startswith('/') or path.startswith('//'): raise ValueError('无效的站点路径')
    url=BASE+path
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; MovieHelper/1.0)'})
    with urllib.request.urlopen(req,timeout=25) as r:
        if urllib.parse.urlsplit(r.geturl()).hostname!='www.seedhub.cc': raise ValueError('站点跳转到其他域名')
        raw=r.read(MAX_PAGE+1)
        if len(raw)>MAX_PAGE: raise ValueError('页面过大')
        page=raw.decode('utf-8','replace')
        if 'Just a moment' in page or 'Checking your browser' in page: raise ValueError('SeedHub 要求浏览器验证，请稍后重试或手动打开网站')
        return page

def search(title):
    return parse_links(fetch('/s/'+urllib.parse.quote(title,safe='')+'/'))

def versions(path):
    if not re.fullmatch(r'/movies/\d+/?',path): raise ValueError('无效影片地址')
    return [(a,b) for a,b in parse_links(fetch(path)) if b.startswith('/link_start/')]

def get_magnet(path):
    u=urllib.parse.urlsplit(path)
    if u.path!='/link_start/' or not re.fullmatch(r'\d+',urllib.parse.parse_qs(u.query).get('seed_id',[''])[0]): raise ValueError('无效资源地址')
    return parse_magnet(fetch(path))

def private_ip(value):
    ip=ipaddress.ip_address(value)
    if not ip.is_private or ip.is_loopback or ip.is_unspecified or ip.is_link_local or ip.is_multicast: raise ValueError('NAS 地址必须为局域网私有 IP')
    return str(ip)

def connect_pinned(host, port, expected):
    host=private_ip(host); expected=expected.lower().replace(':','').strip()
    if not re.fullmatch(r'[0-9a-f]{64}', expected): raise ValueError('请输入完整的 SHA-256 证书指纹')
    class PinnedConnection(http.client.HTTPSConnection):
        def connect(self):
            super().connect()
            actual=hashlib.sha256(self.sock.getpeercert(binary_form=True)).hexdigest()
            if not __import__('hmac').compare_digest(actual,expected):
                self.close(); raise ValueError('NAS 证书指纹不匹配，已终止连接')
    c=PinnedConnection(host,int(port),context=ssl._create_unverified_context(),timeout=15)
    c.connect()
    return c

def send_qnap(host,port,fingerprint,user,password,magnets,temp,move):
    c=connect_pinned(host,port,fingerprint)
    try:
        form=urllib.parse.urlencode({'user':user,'pass':base64.b64encode(password.encode()).decode()})
        c.request('POST','/downloadstation/V5/Misc/Login',body=form,headers={'Content-Type':'application/x-www-form-urlencoded'})
        r=c.getresponse(); payload=r.read(100000)
        if r.status!=200: raise ValueError('登录请求失败，HTTP '+str(r.status))
        obj=json.loads(payload); sid=obj.get('sid')
        if not sid: raise ValueError('登录失败；请检查账号、权限和两步验证支持')
        results=[]
        for magnet in magnets:
            if not re.match(r'^magnet:\?xt=urn:btih:[0-9a-zA-Z]{32,40}(?:&|$)',magnet,re.I): raise ValueError('无效磁力链接')
            query=urllib.parse.urlencode({'sid':sid,'url':magnet,'temp':temp,'move':move})
            c.request('GET','/downloadstation/V5/Task/AddUrl?'+query)
            r=c.getresponse(); data=r.read(100000)
            try: ok=r.status==200 and json.loads(data).get('error')==0
            except (ValueError,AttributeError): ok=False
            results.append(ok)
        return results
    finally: c.close()

class App:
    def __init__(self):
        self.root=tk.Tk(); self.root.title('想看电影资源助手'); self.root.geometry('980x760'); self.movies=[]; self.results=[]; self.resources=[]; self.queue=[]
        top=ttk.Frame(self.root,padding=10);top.pack(fill='x')
        ttk.Button(top,text='1. 导入想看 CSV',command=self.load).pack(side='left');self.info=ttk.Label(top,text='请先在电影清单导出想看 CSV');self.info.pack(side='left',padx=12)
        frame=ttk.Frame(self.root,padding=10);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='想看电影（双击填入搜索词）').grid(row=0,column=0,sticky='w');ttk.Label(frame,text='SeedHub 影片候选（核对年份后双击）').grid(row=0,column=1,sticky='w')
        self.movie=tk.Listbox(frame,height=10,exportselection=False);self.movie.grid(row=1,column=0,sticky='nsew',padx=(0,5));self.movie.bind('<Double-Button-1>',self.choose_movie)
        self.match=tk.Listbox(frame,height=10,exportselection=False);self.match.grid(row=1,column=1,sticky='nsew');self.match.bind('<Double-Button-1>',self.choose_match)
        controls=ttk.Frame(frame);controls.grid(row=2,column=0,columnspan=2,sticky='ew',pady=8);ttk.Label(controls,text='搜索词（支持中文）').pack(side='left');self.word=ttk.Entry(controls);self.word.pack(side='left',fill='x',expand=True,padx=6);ttk.Button(controls,text='2. 查询',command=self.do_search).pack(side='left');ttk.Button(controls,text='查询全部想看',command=self.search_all).pack(side='left',padx=6);ttk.Button(controls,text='打开候选网页核对',command=self.open_match).pack(side='left')
        ttk.Label(frame,text='资源版本（可多选，注意清晰度、字幕和大小）').grid(row=3,column=0,columnspan=2,sticky='w');self.vers=tk.Listbox(frame,height=10,selectmode='extended',exportselection=False);self.vers.grid(row=4,column=0,columnspan=2,sticky='nsew');ttk.Button(frame,text='3. 获取所选磁力并加入队列',command=self.add_queue).grid(row=5,column=0,columnspan=2,sticky='w',pady=6)
        ttk.Label(frame,text='待处理队列').grid(row=6,column=0,sticky='w');self.q=tk.Listbox(frame,height=6,selectmode='extended',exportselection=False);self.q.grid(row=7,column=0,columnspan=2,sticky='nsew')
        bar=ttk.Frame(frame);bar.grid(row=8,column=0,columnspan=2,sticky='w',pady=7);ttk.Button(bar,text='复制全部磁力',command=self.copy).pack(side='left');ttk.Button(bar,text='删除所选',command=self.remove).pack(side='left',padx=6);ttk.Button(bar,text='发送至 Download Station',command=self.send).pack(side='left')
        frame.columnconfigure(0,weight=1);frame.columnconfigure(1,weight=1);frame.rowconfigure(4,weight=1);self.status=ttk.Label(self.root,text='准备就绪',padding=10);self.status.pack(fill='x')
    def work(self,fn,done):
        self.status.config(text='处理中，请稍候…')
        def run():
            try: value=fn();self.root.after(0,lambda: (done(value),self.status.config(text='完成')))
            except Exception as e:
                msg=str(e);self.root.after(0,lambda: (self.status.config(text='操作未完成'),messagebox.showerror('操作失败',msg)))
        threading.Thread(target=run,daemon=True).start()
    def load(self):
        path=filedialog.askopenfilename(filetypes=[('CSV','*.csv')]);
        if not path:return
        try:
            with open(path,encoding='utf-8-sig',newline='') as f:self.movies=list(csv.DictReader(f))
            self.movie.delete(0,'end')
            for x in self.movies:self.movie.insert('end',x.get('片名','')+' ('+x.get('年份','')+')')
            self.info.config(text=f'已导入 {len(self.movies)} 部影片')
        except Exception as e: messagebox.showerror('导入失败',str(e))
    def choose_movie(self,event=None):
        if not self.movie.curselection():return
        self.word.delete(0,'end');self.word.insert(0,self.movies[self.movie.curselection()[0]].get('片名',''))
    def do_search(self):
        term=self.word.get().strip()
        if not term:return
        def done(items):
            self.results=items;self.match.delete(0,'end')
            for title,path in items:self.match.insert('end',title)
            if not items:messagebox.showinfo('没有结果','可尝试输入中文片名。')
        self.work(lambda:search(term),done)
    def search_all(self):
        if not self.movies:return
        titles=[x.get('片名','').strip() for x in self.movies if x.get('片名','').strip()]
        def retrieve():
            found=[];errors=[]
            for title in titles:
                try:
                    items=search(title)
                    found.extend((title+' → '+label,path) for label,path in items)
                except Exception:errors.append(title)
                time.sleep(0.5)
            return found,errors
        def done(value):
            self.results,errors=value;self.match.delete(0,'end')
            for title,_ in self.results:self.match.insert('end',title)
            messagebox.showinfo('批量查询',f'找到 {len(self.results)} 条候选；{len(errors)} 部查询失败。请逐一核对影片和年份；可用中文片名单独重试。')
        self.work(retrieve,done)
    def open_match(self):
        if self.match.curselection():webbrowser.open(BASE+self.results[self.match.curselection()[0]][1])
    def choose_match(self,event=None):
        if not self.match.curselection():return
        path=self.results[self.match.curselection()[0]][1]
        def done(items):
            self.resources=items;self.vers.delete(0,'end')
            for title,_ in items:self.vers.insert('end',title)
        self.work(lambda:versions(path),done)
    def add_queue(self):
        items=[self.resources[i] for i in self.vers.curselection()]
        if not items:return
        def done(found):
            for title,magnet in found:
                if all(m!=magnet for _,m in self.queue):self.queue.append((title,magnet));self.q.insert('end',title)
        def retrieve():return [(title,get_magnet(path)) for title,path in items]
        self.work(retrieve,done)
    def copy(self):
        if self.queue:self.root.clipboard_clear();self.root.clipboard_append('\n'.join(m for _,m in self.queue));self.status.config(text='已复制，可粘贴到 Download Station 的“输入 URL”')
    def remove(self):
        for i in reversed(self.q.curselection()):self.q.delete(i);del self.queue[i]
    def send(self):
        if not self.queue:return
        host=simpledialog.askstring('NAS','局域网 IP：',initialvalue='192.168.1.2',parent=self.root)
        if not host:return
        port=simpledialog.askinteger('NAS','HTTPS 端口：',initialvalue=443,parent=self.root)
        if not port:return
        fingerprint=simpledialog.askstring('NAS','输入 NAS 证书的 SHA-256 指纹（请通过可信渠道核对）：',parent=self.root)
        if not fingerprint:return
        user=simpledialog.askstring('NAS','管理员账号：',parent=self.root)
        if not user:return
        password=simpledialog.askstring('NAS','管理员密码（仅本次使用）：',show='*',parent=self.root)
        if password is None:return
        temp=simpledialog.askstring('NAS','临时文件目录：',initialvalue='下载',parent=self.root)
        if temp is None:return
        move=simpledialog.askstring('NAS','完成后目录：',initialvalue='下载',parent=self.root)
        if move is None:return
        if not messagebox.askyesno('确认发送',f'向 NAS 添加 {len(self.queue)} 个下载任务？'):return
        magnets=[m for _,m in self.queue]
        def done(results):messagebox.showinfo('发送结果',f'成功 {sum(results)} 项，失败 {len(results)-sum(results)} 项。请到 Download Station 查看。')
        self.work(lambda:send_qnap(host,port,fingerprint,user,password,magnets,temp,move),done)

if __name__=='__main__': App().root.mainloop()
