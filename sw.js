/* BPCO OOH*PRODUCTION — service worker
 * 목적: Android Chrome '앱 설치' 요건 충족 + 오프라인 시 마지막 화면 표시.
 * 원칙:
 *   - same-origin GET 요청만 다룬다. Supabase(실시간 DB)·CDN·API 요청은 절대 가로채지 않는다.
 *   - network-first: 항상 네트워크를 먼저 시도해 코드 수정이 즉시 반영된다.
 *     네트워크가 실패했을 때만 캐시로 대체한다.
 */
var CACHE = 'bpco-shell-v1';

self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil((async function () {
    try {
      var keys = await caches.keys();
      await Promise.all(keys.map(function (k) {
        return k === CACHE ? null : caches.delete(k);
      }));
    } catch (e) {}
    try { await self.clients.claim(); } catch (e) {}
  })());
});

self.addEventListener('fetch', function (event) {
  var req = event.request;

  // 읽기 전용 same-origin 요청만 처리. POST/PUT 등과 외부 요청은 그대로 통과.
  if (req.method !== 'GET') return;

  var url;
  try { url = new URL(req.url); } catch (e) { return; }
  if (url.origin !== self.location.origin) return;   // Supabase · cdn.jsdelivr 등
  if (url.pathname.indexOf('/bpco1/') !== 0) return; // 이 앱 범위 밖
  if (url.pathname.slice(-6) === '/sw.js') return;   // 워커 자신은 캐시하지 않음

  event.respondWith((async function () {
    try {
      var res = await fetch(req, { cache: 'no-store' });
      if (res && res.ok && res.type === 'basic') {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(req, copy); }).catch(function () {});
      }
      return res;
    } catch (e) {
      var cached = await caches.match(req, { ignoreSearch: true });
      if (cached) return cached;
      throw e;
    }
  })());
});
