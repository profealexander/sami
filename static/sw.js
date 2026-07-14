self.addEventListener('install', (e) => {
    console.log('[Service Worker] Install');
});
self.addEventListener('fetch', (e) => {
    // Máximo rendimiento: pasamos directo a la red sin caché
});
