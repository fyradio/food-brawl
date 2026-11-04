#!/usr/bin/env python3
"""通用：單檔 HTML 遊戲/網頁 → 離線 PWA → GitHub Pages 一鍵發佈。
用法: python3 gamerelease.py CONFIG.json "更新說明" [patch|minor|major|none]
CONFIG.json 欄位:
  src      來源 html 完整路徑            (必填)
  repo     GitHub Pages repo 本機路徑     (必填；已 clone、已有 remote)
  title    完整名稱   short 主畫面短名   theme 主題色(#hex)   lang (預設 zh-Hant)
  sw       service worker 快取名前綴(英文)
  icon     自訂圖示 PNG 路徑(可省略，省略就畫一個通用陀螺圖示)
  assets   要一起預先快取的相對路徑清單(如 ["music/a.mp3"])，可省略
  wrapped  true=repo 的 index.html 本身就是完整 PWA(沒有另外的來源檔)：src 填 repo/index.html，
           只做 語法檢查→版本號+1→sw.js 內 const V='前綴-vN' 的 N+1→commit/push，不重新產生 index.html
  trailers commit 結尾署名行陣列，可省略
  artifact 該遊戲的 Artifact 網址(僅提示用)
步驟: 語法檢查 → 版本號(.ver 或 class 含 ver 的 vX.Y.Z)+1 → SW 版本+1 → 產生 index.html/sw.js → git commit+push
之後 Claude 要用 Artifact 工具發佈 src。"""
import sys,re,json,os,io,base64,subprocess,math
cfg=json.load(open(sys.argv[1]));msg=sys.argv[2];lv=sys.argv[3] if len(sys.argv)>3 else 'patch'
SRC,REPO=cfg['src'],cfg['repo'];T=cfg.get('title','Game');SH=cfg.get('short',T);TH=cfg.get('theme','#0a0f1f');LG=cfg.get('lang','zh-Hant');SW=cfg.get('sw','game')
s=open(SRC,encoding='utf-8').read()
WRAP=bool(cfg.get('wrapped'))
# 1 語法檢查（每個內嵌 script）
chk="const s=require('fs').readFileSync(process.argv[1],'utf8');const m=[...s.matchAll(/<script>([\\s\\S]*?)<\\/script>/g)];m.forEach(x=>new Function(x[1]));console.log('syntax ok ('+m.length+' scripts)')"
subprocess.run(['node','-e',chk,SRC],check=True)
# 2 版本號
ver=None;m=re.search(r'(class="[^"]*\bver\b[^"]*"[^>]*>\s*v)(\d+)\.(\d+)\.(\d+)',s)
if m and lv!='none':
    a,b,c=int(m[2]),int(m[3]),int(m[4])
    a,b,c={'major':(a+1,0,0),'minor':(a,b+1,0)}.get(lv,(a,b,c+1))
    ver=f'v{a}.{b}.{c}';s=s[:m.start()]+m[1]+f'{a}.{b}.{c}'+s[m.end():];open(SRC,'w',encoding='utf-8').write(s)
elif m: ver='v'+'.'.join(m.groups()[1:])
if WRAP:
    swp=os.path.join(REPO,'sw.js');sw=open(swp).read()
    mm=re.search(r"(const V=')([^']*?)(\d+)(')",sw)
    sw=sw[:mm.start()]+mm[1]+mm[2]+str(int(mm[3])+1)+mm[4]+sw[mm.end():];open(swp,'w').write(sw);n=mm[2]+str(int(mm[3])+1)
if not WRAP:
    # 3 SW 版本計數存在 repo/.swver
    vf=os.path.join(REPO,'.swver');n=int(open(vf).read())+1 if os.path.exists(vf) else 1;open(vf,'w').write(str(n))
    # 4 外部資源：移除 Google Fonts（離線會卡），外部 script 加 crossorigin 並預先快取
    s=re.sub(r'<link[^>]*fonts\.googleapis\.com[^>]*>\n?','',s)
    s=re.sub(r'<meta name="claude:[^>]*>\n?','',s)
    ext=re.findall(r'<script[^>]*\ssrc="(https?://[^"]+)"',s)
    for u in ext:
        s=re.sub(r'(<script(?![^>]*crossorigin)[^>]*\ssrc="'+re.escape(u)+r'")',r'\1 crossorigin="anonymous"',s)
    # 5 圖示
    from PIL import Image,ImageDraw
    def icon(n):
        if cfg.get('icon') and os.path.exists(cfg['icon']): im=Image.open(cfg['icon']).convert('RGBA').resize((n,n),Image.LANCZOS)
        else:
            S=n*4;im=Image.new('RGB',(S,S),(10,15,31));d=ImageDraw.Draw(im);c=S/2
            for r,col in [(0.46,(40,60,140)),(0.40,(255,200,61))]:d.ellipse([c-S*r,c-S*r,c+S*r,c+S*r],fill=col)
            pts=[]
            for i in range(240):
                th=i/240*2*math.pi;t=(th/(2*math.pi)*3)%1;rr=0.78+0.42*(t**1.6)*(1 if t<0.88 else (1-t)/0.12);pts.append((c+math.cos(th)*rr*S*0.3,c+math.sin(th)*rr*S*0.3))
            d.polygon(pts,fill=(255,59,47));d.ellipse([c-S*0.17,c-S*0.17,c+S*0.17,c+S*0.17],fill=(190,198,220));d.ellipse([c-S*0.1,c-S*0.1,c+S*0.1,c+S*0.1],fill=(63,208,255))
            im=im.resize((n,n),Image.LANCZOS)
        b=io.BytesIO();im.save(b,'PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
    i192,i512,i180=icon(192),icon(512),icon(180)
    man={"name":T,"short_name":SH,"start_url":"./","scope":"./","display":"fullscreen","orientation":"any","background_color":TH,"theme_color":TH,"icons":[{"src":i192,"sizes":"192x192","type":"image/png"},{"src":i512,"sizes":"512x512","type":"image/png","purpose":"any maskable"}]}
    manu='data:application/manifest+json;base64,'+base64.b64encode(json.dumps(man,ensure_ascii=False).encode()).decode()
    head=f'''<!doctype html>
    <html lang="{LG}"><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="{SH}">
    <meta name="theme-color" content="{TH}">
    <link rel="manifest" href="{manu}">
    <link rel="apple-touch-icon" href="{i180}">
    <link rel="icon" type="image/png" href="{i192}">
    <style>:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0;font-size:14px;font-family:system-ui,sans-serif}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
    </head><body>
    '''
    tail='''
    <script>if('serviceWorker' in navigator){let hadCtl=!!navigator.serviceWorker.controller,rl=false;navigator.serviceWorker.addEventListener('controllerchange',()=>{if(hadCtl&&!rl){rl=true;location.reload()}hadCtl=true});addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}))}</script>
    </body></html>
    '''
    open(os.path.join(REPO,'index.html'),'w',encoding='utf-8').write(head+s+tail)
    pre=json.dumps(['./','./index.html']);opt=json.dumps(cfg.get('assets',[]));exts=json.dumps(ext)
    open(os.path.join(REPO,'sw.js'),'w').write(f'''const V='{SW}-v{n}';
    const EXT={exts};
    self.addEventListener('install',e=>{{e.waitUntil(caches.open(V).then(c=>c.addAll({pre}).then(()=>Promise.all([...{opt}.map(u=>c.add(u).catch(()=>{{}})),...EXT.map(u=>c.add(new Request(u,{{mode:'cors'}})).catch(()=>{{}}))])))).then(()=>self.skipWaiting()));}});
    self.addEventListener('activate',e=>{{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));}});
    self.addEventListener('fetch',e=>{{
      if(e.request.method!=='GET')return;
      const same=new URL(e.request.url).origin===location.origin;
      e.respondWith((same?fetch(e.request.url,{{cache:'no-store'}}):fetch(e.request)).then(r=>{{const cp=r.clone();caches.open(V).then(c=>c.put(e.request,cp));return r}}).catch(()=>caches.match(e.request,{{ignoreSearch:true}})));
    }});
    ''')
# 6 git
def ensure_pages(cfg):
    """GitHub Pages 有時會漏建（兩次 push 間隔太短時，後一次不會觸發 pages build）。
    push 後查 actions runs：遠端 HEAD 有沒有 pages 建置、有沒有成功；90 秒內沒出現就推一個空 commit 重觸發，最多 2 次。"""
    import time,re as _re
    if cfg.get('pages') is False:return
    url=subprocess.run(['git','remote','get-url','origin'],cwd=REPO,capture_output=True,text=True).stdout.strip()
    m=_re.search(r'github\.com[/:]([^/]+)/([^/.]+)',url)
    if not m:return
    slug=f'{m.group(1)}/{m.group(2)}'
    def runs(sha):
        r=subprocess.run(['gh','api',f'repos/{slug}/actions/runs?head_sha={sha}&per_page=5'],capture_output=True,text=True)
        if r.returncode:return None
        try:return [x for x in json.loads(r.stdout).get('workflow_runs',[]) if 'pages' in x.get('name','').lower()]
        except Exception:return None
    for attempt in range(3):
        sha=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,text=True).stdout.strip()
        rem=subprocess.run(['git','ls-remote','origin','refs/heads/main'],cwd=REPO,capture_output=True,text=True).stdout.split()[:1]
        if rem!=[sha]:print('⚠ 遠端 main 跟本地不同，重推');subprocess.run(['git','push','-q'],cwd=REPO)
        t0=time.time();seen=None
        while time.time()-t0<240:
            rs=runs(sha)
            if rs is None:print('（無法查 GitHub Actions，請手動確認 Pages）');return
            if rs:
                seen=rs[0]
                if seen['status']=='completed':break
            elif time.time()-t0>90:break
            time.sleep(10)
        if seen and seen['status']=='completed' and seen['conclusion']=='success':
            print(f'✔ Pages 已部署 {sha[:7]}');return
        if seen and seen['status']!='completed':print(f'⚠ Pages 建置 {sha[:7]} 還在跑（{seen["status"]}），稍後再查');return
        print(f'⚠ Pages 沒有建置 {sha[:7]}（{seen and seen["conclusion"]}），推空 commit 重觸發')
        tr='\n'.join(cfg.get('trailers',[]))
        subprocess.run(['git','commit','-q','--allow-empty','-m','Trigger Pages rebuild'+('\n\n'+tr if tr else '')],cwd=REPO,check=True)
        subprocess.run(['git','push','-q'],cwd=REPO,check=True)
    print('✘ Pages 重試後仍未部署，請到 GitHub 的 Actions 頁面查看')
tr='\n'.join(cfg.get('trailers',[]));full=f'{ver or "update"}: {msg}'+('\n\n'+tr if tr else '')
run=lambda *a:subprocess.run(a,cwd=REPO,check=True)
run('git','add','-A')
if subprocess.run(['git','diff','--cached','--quiet'],cwd=REPO).returncode:
    run('git','commit','-qm',full)
    if subprocess.run(['git','remote'],cwd=REPO,capture_output=True,text=True).stdout.strip():
        run('git','push','-q');ensure_pages(cfg)
print(f'released {ver} (sw {SW}-v{n}) → 接著用 Artifact 工具發佈 {SRC}'+(f' url={cfg["artifact"]}' if cfg.get('artifact') else ''))
