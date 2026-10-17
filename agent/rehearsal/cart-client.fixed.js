// Cart API client, written by the site's third-party web agency.
// Used by the shop page (index.html) and by the health check (monitor/healthcheck.mjs).
// API reference: site/VENDOR_API.md

export class ApiError extends Error {
  constructor(status, endpoint) {
    super(`${endpoint} failed with HTTP ${status}`);
    this.status = status;
    this.endpoint = endpoint;
  }
}

// The vendor sheds load with temporary 429/502/503/504 errors; retry those a few times.
const RETRYABLE = new Set([429, 502, 503, 504]);
const MAX_ATTEMPTS = 4;
const sleep = ms => new Promise(r => setTimeout(r, ms));
// crypto.randomUUID only exists on https/localhost in browsers; the shop is also served over plain http.
const newKey = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;

async function post(baseUrl, path, body) {
  // One key per logical action, reused on every retry, so a retried 504 is never applied twice.
  const idempotencyKey = newKey();
  for (let attempt = 1; ; attempt++) {
    let res;
    try {
      res = await fetch(baseUrl + path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
        body: JSON.stringify(body),
      });
    } catch (err) {
      if (attempt >= MAX_ATTEMPTS) throw err;
      await sleep(150 * 2 ** (attempt - 1));
      continue;
    }
    if (res.ok) return res.json();
    if (!RETRYABLE.has(res.status) || attempt >= MAX_ATTEMPTS) throw new ApiError(res.status, path);
    const retryAfter = Number(res.headers.get("Retry-After"));
    await sleep(retryAfter > 0 ? Math.min(retryAfter * 1000, 2000) : 150 * 2 ** (attempt - 1));
  }
}

// Adds one item to the cart. Resolves to { cart: { itemId: qty }, count }.
export function addToCart(baseUrl, cartId, itemId) {
  return post(baseUrl, "/api/cart/add", { cartId, itemId });
}

// Saves the customer's choices (size, toppings) for a pizza they are building.
// options: { itemId, size, toppings: [..] }. Resolves to { lineId, options }.
export function saveOption(baseUrl, cartId, lineId, options) {
  return post(baseUrl, "/api/cart/option", { cartId, lineId, options });
}

// Places the order. Resolves to { orderId, slot }.
export function checkout(baseUrl, cartId, slot) {
  return post(baseUrl, "/api/checkout", { cartId, slot });
}
