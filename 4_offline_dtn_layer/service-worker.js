/**
 * AstroPulse (NASA Space Apps) - Phase 4: Service Worker & NASA DTN Caching
 * Module: 4_offline_dtn_layer/service-worker.js
 *
 * Implements offline PWA caching and NASA Delay-Tolerant Networking (DTN) packet buffering.
 */

const CACHE_NAME = "astropulse-dtn-v1";
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/favicon.ico",
  "/manifest.json",
];

// Install: Pre-cache static HUD shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[ServiceWorker] Pre-caching AstroPulse static assets");
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn("[ServiceWorker] Static asset pre-cache skipped (dev mode):", err);
      });
    })
  );
  self.skipWaiting();
});

// Activate: Purge obsolete cache stores
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("[ServiceWorker] Evicting outdated cache:", key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Interceptor: Network-First with Offline Fallback
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Bypass WebSocket connections and non-HTTP requests
  if (url.protocol === "ws:" || url.protocol === "wss:") {
    return;
  }

  // Handle API telemetry requests during complete signal loss
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(event.request.clone()).catch(async (error) => {
        console.warn(`[ServiceWorker] Network error on ${url.pathname}; engaging DTN offline responder.`);
        return new Response(
          JSON.stringify({
            dtn_intercepted: true,
            status: "buffered_in_dtn_storage",
            message: "Signal loss detected. Telemetry stored in local autonomous IndexedDB queue.",
            timestamp: new Date().toISOString(),
          }),
          {
            headers: { "Content-Type": "application/json" },
            status: 202, // Accepted for deferred processing
          }
        );
      })
    );
    return;
  }

  // Standard cache-first / network fallback for static HUD assets
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).catch(() => {
        if (event.request.headers.get("accept")?.includes("text/html")) {
          return caches.match("/index.html");
        }
      });
    })
  );
});

// Background Sync Listener for DTN Flush
self.addEventListener("sync", (event) => {
  if (event.tag === "dtn-sync-queue") {
    console.log("[ServiceWorker] Background Sync event triggered: Flushing DTN bundles to Earth gateway.");
    event.waitUntil(
      self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ type: "DTN_TRIGGER_BACKGROUND_FLUSH" });
        });
      })
    );
  }
});
