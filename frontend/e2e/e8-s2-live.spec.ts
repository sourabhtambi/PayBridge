import { test, expect } from "@playwright/test";

const API = "http://localhost:8000";
const SS = "../specs/reviews/screenshots/e8-s2/";
const cust = { "X-Role": "customer", "X-Customer-Id": "cus_001" };
const admin = { "X-Role": "admin" };
const seed = (role: string, customerId: string | null) => ({ role, customerId });

test("E8-S2 live dashboard as admin", async ({ page, request }) => {
  const res = await request.post(`${API}/payments`, {
    headers: { ...cust, "Idempotency-Key": `e8s2-${Date.now()}` },
    data: { amount_paise: 777700, beneficiary: "E8S2 Live" },
  });
  expect(res.status()).toBeLessThan(300);
  const id = (await res.json()).id as string;
  let done = false;
  for (let i = 0; i < 40 && !done; i++) {
    done = (await (await request.get(`${API}/payments/${id}`, { headers: cust })).json()).state === "COMPLETED";
    if (!done) await new Promise((s) => setTimeout(s, 500));
  }
  expect(done).toBe(true);
  const rr = await request.post(`${API}/refunds`, { headers: cust, data: { payment_id: id } });
  expect(rr.status()).toBe(201);

  let summaryCalls = 0;
  page.on("request", (r) => { if (r.url().startsWith(`${API}/dashboard/summary`)) summaryCalls++; });
  // Freeze the initial today-summary: capture one real API response and serve that
  // same body to the UI, so assertions compare against exactly what the UI received.
  type Summary = {
    rails: { rail: string; payment_count: number }[];
    status_counts: Record<string, number>;
    pending_refunds: { payment_id: string }[];
  };
  let frozen = true;
  let before: Summary | null = null;
  await page.route(`${API}/dashboard/summary*`, async (route) => {
    if (!frozen || route.request().url().includes("date=2026-01-01")) return route.continue();
    const real = await route.fetch();
    before ??= (await real.json()) as Summary;
    return route.fulfill({ response: real, json: before });
  });
  await page.addInitScript((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), seed("admin", null));
  await page.goto("/dashboard");
  await expect(page.getByRole("navigation").getByRole("link")).toHaveText(["Dashboard", "Settlement", "Simulation"]);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  // real data in tiles
  await expect.poll(() => before !== null).toBe(true);
  const snap = before as unknown as Summary;
  expect(snap.pending_refunds.some((r) => r.payment_id === id)).toBe(true);
  for (const r of snap.rails) {
    await expect(page.locator(`[data-rail="${r.rail}"] [data-field="payment_count"]`)).toHaveText(String(r.payment_count));
  }
  await expect(page.locator('[data-rail="UPI"]')).toContainText("Rs ");
  for (const s of ["CREATED", "SUBMITTED", "COMPLETED", "FAILED"]) {
    await expect(page.locator(`[data-status="${s}"] [data-field="status_counts.${s}"]`)).toHaveText(String(snap.status_counts[s]));
  }
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
  await expect(page.getByLabel("Date (IST)")).toHaveValue(today);
  const pendingBefore = snap.pending_refunds.length;
  await expect(page.locator('[data-field="pending_count"]')).toHaveText(`${pendingBefore} pending`);
  await page.waitForTimeout(500);
  console.log("SUMMARY_CALLS_ON_LOAD", summaryCalls);
  await page.screenshot({ path: SS + "01-live-today.png", fullPage: true });

  // approve from tile
  const approve = page.getByRole("button", { name: `Approve refund for payment ${id}` });
  await expect(approve).toBeVisible();
  frozen = false;
  const postP = page.waitForRequest((r) => r.url().endsWith("/approve") && r.method() === "POST");
  await approve.click();
  expect((await postP).headers()["x-role"]).toBe("admin");
  await expect(page.locator(`tr[data-id]`).filter({ hasText: id }).getByText("EXECUTED")).toBeVisible();
  await expect(page.locator('[data-field="pending_count"]')).toHaveText(/^\d+ pending$/);
  await page.screenshot({ path: SS + "02-live-approved.png", fullPage: true });
  const pay = await (await request.get(`${API}/payments/${id}`, { headers: cust })).json();
  expect(pay.refund.state).toBe("EXECUTED");

  // date picker: past empty date
  await page.getByLabel("Date (IST)").fill("2026-01-01");
  await expect(page.getByText("No activity for this date")).toBeVisible();
  for (const r of ["UPI", "IMPS", "NEFT", "RTGS"]) {
    await expect(page.locator(`[data-rail="${r}"] [data-field="payment_count"]`)).toHaveText("0");
  }
  await expect(page.locator('[data-status="COMPLETED"] [data-field="status_counts.COMPLETED"]')).toHaveText("0");
  await page.screenshot({ path: SS + "03-live-empty-date.png", fullPage: true });
  await expect(page.getByLabel("Date (IST)")).toHaveAttribute("max", today);

  // F019 other roles
  for (const [role, cid, links] of [["ops", null, ["Reconciliation", "Stuck payments"]], ["customer", "cus_001", ["Payments"]]] as const) {
    const ctx = await page.context().browser()!.newContext();
    const p = await ctx.newPage();
    await p.addInitScript((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), seed(role, cid));
    await p.goto("http://localhost:3000/");
    await expect(p.getByRole("navigation").getByRole("link")).toHaveText([...links]);
    await ctx.close();
  }
});

test("E8-S2 live /refunds regression", async ({ page, request }) => {
  const res = await request.post(`${API}/payments`, {
    headers: { ...cust, "Idempotency-Key": `e8s2r-${Date.now()}` },
    data: { amount_paise: 123400, beneficiary: "E8S2 Reg" },
  });
  const id = (await res.json()).id as string;
  for (let i = 0; i < 40; i++) {
    if ((await (await request.get(`${API}/payments/${id}`, { headers: cust })).json()).state === "COMPLETED") break;
    await new Promise((s) => setTimeout(s, 500));
  }
  expect((await request.post(`${API}/refunds`, { headers: cust, data: { payment_id: id } })).status()).toBe(201);
  await page.addInitScript((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), seed("admin", null));
  await page.goto("/refunds");
  await expect(page.getByRole("heading", { name: "Refund queue" })).toBeVisible();
  await page.getByRole("button", { name: `Reject refund for payment ${id}` }).click();
  await expect(page.getByRole("row").filter({ hasText: id }).getByText("REJECTED")).toBeVisible();
  await page.screenshot({ path: SS + "04-refunds-route.png", fullPage: true });
});
