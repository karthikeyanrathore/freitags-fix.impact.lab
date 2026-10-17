# Ordering API (hosting vendor)

Base URL: same origin as the shop. All bodies are JSON.

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/cart/add` | `{ cartId, itemId }` | `{ cart: { itemId: qty }, count }` |
| GET | `/api/cart?cartId=…` | | `{ cart, count }` |
| POST | `/api/checkout` | `{ cartId, slot }` | `{ orderId, slot }` |

## Reliability notes from the vendor
- At busy times the platform sheds load. Clients may receive **429 Too Many Requests** (with a `Retry-After` header in seconds), **503 Service Unavailable** or **504 Gateway Timeout**. These are temporary; the same request usually succeeds when retried shortly after.
- A **504** means the gateway gave up waiting. The request **may already have been applied**. Retrying a POST without an idempotency key can apply it twice (for example, two pizzas instead of one).
- POST endpoints accept an optional **`Idempotency-Key`** header (any unique string, e.g. a UUID). Retries that reuse the same key are applied at most once and return the original result.
- Recommended client behaviour: retry 429/502/503/504 and network errors a few times with backoff, honour `Retry-After`, and send one `Idempotency-Key` per logical action, reused across its retries.
