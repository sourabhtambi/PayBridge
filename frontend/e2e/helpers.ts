import { expect, type APIRequestContext } from "@playwright/test";

const API = "http://localhost:8000";
const CUSTOMER = { "X-Role": "customer", "X-Customer-Id": "cus_001" };

/** Needs a backend started with PAYBRIDGE_ENV=test (and its own PAYBRIDGE_DATA_DIR). */
export async function resetDb(request: APIRequestContext): Promise<void> {
  const res = await request.post(`${API}/test/reset`);
  expect(res.status(), "POST /test/reset failed: start the backend with PAYBRIDGE_ENV=test").toBe(200);
}

/** Creates a payment for cus_001 and waits until the outbox worker completes it. */
export async function seedCompletedPayment(
  request: APIRequestContext,
  amountPaise: number,
  beneficiary = "Seed",
): Promise<string> {
  const res = await request.post(`${API}/payments`, {
    headers: { ...CUSTOMER, "Idempotency-Key": `seed-${Date.now()}-${Math.random()}` },
    data: { amount_paise: amountPaise, beneficiary },
  });
  expect(res.status()).toBeLessThan(300);
  const id = (await res.json()).id as string;
  for (let i = 0; i < 40; i++) {
    const p = await (await request.get(`${API}/payments/${id}`, { headers: CUSTOMER })).json();
    if (p.state === "COMPLETED") return id;
    await new Promise((s) => setTimeout(s, 250));
  }
  throw new Error(`payment ${id} did not complete`);
}
