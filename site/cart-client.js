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

async function post(baseUrl, path, body) {
  const res = await fetch(baseUrl + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, path);
  return res.json();
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
