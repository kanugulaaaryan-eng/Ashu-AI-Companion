const CACHE = 'ashu-v0.9-static-v1';
const ASSETS = [
  './ashu_prototype.html',
  './ashu_companion.html',
  './favicon.svg',
  './icon-192.png',
  './icon-512.png',
  './manifest.webmanifest',
  './tauri-bridge.js'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;
  
  const url = new URL(event.request.url);
  
  // Skip cross-origin requests, chrome-extension, and other unsupported schemes
  if (url.origin !== location.origin) return;
  if (url.protocol === 'chrome-extension:' || url.protocol === 'chrome:' || url.protocol === 'moz-extension:') return;
  
  // Skip API calls - let them go to network
  if (url.pathname.startsWith('/v1/')) return;
  
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      
      return fetch(event.request).then(resp => {
        // Only cache successful same-origin responses
        if (resp.ok && resp.type === 'basic') {
          const copy = resp.clone();
          caches.open(CACHE).then(cache => cache.put(event.request, copy));
        }
        return resp;
      }).catch(() => {
        // Fallback to main page for navigation requests
        if (event.request.mode === 'navigate') {
          return caches.match('./ashu_prototype.html');
        }
        throw new Error('Network error');
      });
  });
});