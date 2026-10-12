    const CACHE_NAME = 'spring-quiz-v11-drill-2026';
    const ASSETS = ['./', './index.html', location.href.split('#')[0]];
    self.addEventListener('install', e => {
      e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS).catch(()=>{})).then(()=>self.skipWaiting()));
    });
    self.addEventListener('activate', e => {
      e.waitUntil(
        caches.keys().then(keys => Promise.all(
          keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
        )).then(()=>self.clients.claim())
      );
    });
    self.addEventListener('fetch', e => {
      if(e.request.method !== 'GET') return;
      if(e.request.url.startsWith('blob:') || e.request.url.startsWith('data:')) return;
      // 只缓存同源请求
      const url = new URL(e.request.url);
      if(url.origin !== location.origin && !e.request.url.startsWith(self.location.origin)){
        return; // 跨域请求直接走网络
      }
      e.respondWith(
        caches.match(e.request).then(cached => {
          // stale-while-revalidate：先返回缓存，同时后台更新
          const fetchPromise = fetch(e.request).then(resp => {
            if(resp && (resp.status === 200 || resp.type === 'opaque') && (resp.type === 'basic' || resp.type === 'default')){
              const clone = resp.clone();
              caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
            }
            return resp;
          }).catch(()=>cached);
          return cached || fetchPromise;
        }).catch(()=>{
          // 完全离线时回退到主页面
          return caches.match('./').then(html => html || new Response(
            '<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;padding:40px;"><h2>✈️ 离线模式</h2><p>请在有网络时打开一次页面以启用离线。</p></body></html>',
            {headers:{'Content-Type':'text/html;charset=utf-8'}}
          ));
        })
      );
    });
    self.addEventListener('message', e => {
      if(e.data && e.data.type === 'CLEAR_CACHE'){
        caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
          .then(()=>e.ports[0] && e.ports[0].postMessage({ok:true}));
      }else if(e.data && e.data.type === 'CACHE_STATUS'){
        e.ports[0] && e.ports[0].postMessage({cached: true, version: CACHE_NAME});
      }
    });
