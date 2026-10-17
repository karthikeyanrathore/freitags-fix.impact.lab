// Synthetic customer: runs the shop's real cart client against the API and reports telemetry as JSON.
// Usage: node monitor/healthcheck.mjs --base http://127.0.0.1:8000 --client site/cart-client.js
import { pathToFileURL } from "node:url";
import path from "node:path";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => (a.startsWith("--") ? [...acc, [a.slice(2), all[i + 1]]] : acc), [])
);
const base = args.base || "http://127.0.0.1:8000";
const clientPath = path.resolve(args.client || "site/cart-client.js");
const STEP_BUDGET_MS = 4000; // "latency must be low": any single customer action slower than this fails

const { addToCart, checkout } = await import(pathToFileURL(clientPath).href);
const cartId = "healthcheck-" + Date.now();
const steps = [];

async function step(name, endpoint, fn) {
  const t0 = Date.now();
  try {
    const out = await fn();
    const ms = Date.now() - t0;
    steps.push({ name, endpoint, ok: ms <= STEP_BUDGET_MS, status: 200, latency_ms: ms,
      error: ms > STEP_BUDGET_MS ? `too slow (${ms} ms > ${STEP_BUDGET_MS} ms budget)` : null });
    return out;
  } catch (e) {
    steps.push({ name, endpoint, ok: false, status: e.status ?? null, latency_ms: Date.now() - t0, error: e.message });
    return null;
  }
}

const started = Date.now();
for (const itemId of [1, 2, 13]) {
  await step(`add item ${itemId} to cart`, "/api/cart/add", () => addToCart(base, cartId, itemId));
}

// Every "Add" click must register exactly once.
const cart = await (await fetch(`${base}/api/cart?cartId=${cartId}`)).json();
const added = steps.filter(s => s.endpoint === "/api/cart/add" && s.ok).length;
steps.push({ name: "cart has exactly one of each added item", endpoint: "/api/cart", ok: cart.count === added && added === 3,
  status: null, latency_ms: 0, error: cart.count === added && added === 3 ? null
    : `expected 3 items, cart has ${cart.count} (${added} adds reported success)` });

if (added) await step("checkout", "/api/checkout", () => checkout(base, cartId, "18:30"));

const result = {
  ok: steps.every(s => s.ok),
  timestamp: new Date().toISOString(),
  client: path.relative(process.cwd(), clientPath),
  total_ms: Date.now() - started,
  steps,
};
console.log(JSON.stringify(result));
