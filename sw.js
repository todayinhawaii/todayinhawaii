// Today in Hawaii — Service Worker
const CACHE_NAME = 'todayinhawaii-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/oahu.html',
  '/maui.html',
  '/kauai.html',
  '/bigisland.html',
  '/beaches.html',
  '/hiking.html',
  '/food.html',
  '/about.html',
  '/privacy.html',
  '/banner.jpg',
  '/manifest.json',
];

// Install — cache static assets
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.filter(function(name) {
          return name !== CACHE_NAME;
        }).map(function(name) {
          console.log('[SW] Deleting old cache:', name);
          return caches.delete(name);
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch — network first, cache fallback
self.addEventListener('fetch', function(event) {
  // Skip non-GET and API requests (always fetch live)
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('/api/')) return;
  if (event.request.url.includes('marine-api') || event.request.url.includes('open-meteo')) return;

  event.respondWith(
    fetch(event.request)
      .then(function(response) {
        // Cache successful responses
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(event.request, clone);
          });
        }
        return response;
      })
      .catch(function() {
        // Network failed — serve from cache
        return caches.match(event.request).then(function(cached) {
          if (cached) return cached;
          // Fallback for navigation
          if (event.request.mode === 'navigate') {
            return caches.match('/index.html');
          }
        });
      })
  );
});
