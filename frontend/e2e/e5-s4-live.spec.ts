import { test, expect, type APIRequestContext } from "@playwright/test";
const API = "http://localhost:8000";
const SS = "../specs/reviews/screenshots/e5-s4/";
const cust = { "X-Role": "customer", "X-Customer-Id": "cus_001" };

async function completedPayment(request: APIRequestContext, amount: number): Promise<string> {
  const res = await request.post(`${API}/payments`, {
    headers: { ...cust, "Idempotency-Key": `e5s4-${amount}-${Date.now()}` },
    data: { amount_paise: amount, beneficiary: "E5S4 Live" },
  });
  expect(res.status()).toBeLessThan(300);
  const id = (await res.json()).id as string;
  for (let i = 0; i < 40; i++) {
    const p = await (await request.get(`${API}/payments/${id}`, { headers: cust })).json();
    if (p.state === "COMPLETED") return id;
    await new Promise((s) => setTimeout(s, 500));
  }
  throw new Error("payment never COMPLETED");
}

test("E5-S4 live approve and reject", async ({ page, request }) => {
  const a = await completedPayment(request, 123456);
  const b = await completedPayment(request, 654321);
  for (const id of [a, b]) {
    const r = await request.post(`${API}/refunds`, { headers: cust, data: { payment_id: id } });
    expect(r.status()).toBe(201);
  }
  await page.addInitScript(() => window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "admin", customerId: null })));
  await page.goto("/refunds");
  await expect(page.getByRole("button", { name: `Approve refund for payment ${a}` })).toBeVisible();
  await expect(page.getByText("Rs 1,234.56")).toBeVisible();
  await page.screenshot({ path: SS + "01-live-queue.png", fullPage: true });
  await page.getByRole("button", { name: `Approve refund for payment ${a}` }).click();
  await expect(page.getByRole("row").filter({ hasText: a }).getByText("EXECUTED")).toBeVisible();
  await page.getByRole("button", { name: `Reject refund for payment ${b}` }).click();
  await expect(page.getByRole("row").filter({ hasText: b }).getByText("REJECTED")).toBeVisible();
  await page.screenshot({ path: SS + "02-live-decided.png", fullPage: true });
  const pa = await (await request.get(`${API}/payments/${a}`, { headers: cust })).json();
  expect(pa.refund.state).toBe("EXECUTED");
  const pb = await (await request.get(`${API}/payments/${b}`, { headers: cust })).json();
  expect(pb.refund.state).toBe("REJECTED");
});

test("E5-S4 mocked states screenshots", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "admin", customerId: null })));
  await page.route("http://localhost:8000/refunds?state=REQUESTED", (r) => r.fulfill({ json: { items: [], total: 0 } }));
  await page.goto("/refunds");
  await expect(page.getByText("No refunds pending")).toBeVisible();
  await page.screenshot({ path: SS + "03-empty.png" });
  await page.unroute("http://localhost:8000/refunds?state=REQUESTED");
  await page.route("http://localhost:8000/refunds?state=REQUESTED", (r) => r.fulfill({ status: 500, json: { error: { code: "X", message: "x" } } }));
  await page.goto("/refunds");
  await expect(page.getByRole("button", { name: /retry/i })).toBeVisible();
  await page.screenshot({ path: SS + "04-error.png" });
});
