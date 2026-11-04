const V='food-brawl-v25';
    const EXT=["https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js", "https://cdn.jsdelivr.net/npm/peerjs@1.5.4/dist/peerjs.min.js"];
    self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(["./", "./index.html", "music/lobby-1.mp3", "music/battle-1.mp3"]).then(()=>Promise.all(EXT.map(u=>c.add(new Request(u,{mode:'cors'})).catch(()=>{})))))).then(()=>self.skipWaiting()));});
    self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
    self.addEventListener('fetch',e=>{
      if(e.request.method!=='GET')return;
      const same=new URL(e.request.url).origin===location.origin;
      e.respondWith((same?fetch(e.request.url,{cache:'no-store'}):fetch(e.request)).then(r=>{const cp=r.clone();caches.open(V).then(c=>c.put(e.request,cp));return r}).catch(()=>caches.match(e.request,{ignoreSearch:true})));
    });
    