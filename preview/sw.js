// Offline cache for the handbook. Bump VERSION on every deploy so phones pick up new files.
const VERSION = "xm27-v18";
const FILES = [
  "./", "./index.html", "./manifest.json", "./Xiamen-2027-Handbook.pdf",
   "./img/apple-touch-icon.png",   "./img/dinner-1.jpg",   "./img/dinner-2.jpg",   "./img/dinner-3.jpg",   "./img/hotel-courtyard.jpg",   "./img/hotel-gym.jpg",   "./img/hotel-pool.jpg",   "./img/hotel-room.jpg",   "./img/hotel-suite.jpg",   "./img/hy-1.jpg",   "./img/hy-2.jpg",   "./img/hy-3.jpg",   "./img/icon-192.png",   "./img/icon-512.png",   "./img/trail-1.jpg",   "./img/trail-2.jpg",   "./img/trail-3.jpg",   "./img/trail-4.jpg"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return; // weather etc. go straight to network
  const url = new URL(req.url);
  const isPage = req.mode === "navigate" && (url.pathname.endsWith("/") || url.pathname.endsWith("/index.html"));
  if (isPage) {
    // Page: try the network first so updates show, fall back to the saved copy offline
    // (3s cap: in China a blocked site can hang for a long time instead of failing)
    const net = fetch(req).then(res => {
      const copy = res.clone();
      caches.open(VERSION).then(c => c.put("./index.html", copy));
      return res;
    });
    const timeout = new Promise((_, no) => setTimeout(no, 3000));
    e.respondWith(Promise.race([net, timeout]).catch(() =>
      caches.match("./index.html").then(hit => hit || net)));
    return;
  }
  // Photos, icons: saved copy first
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => hit || fetch(req)));
});
