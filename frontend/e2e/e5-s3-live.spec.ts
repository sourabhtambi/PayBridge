import { test, expect } from "@playwright/test";
import { resetDb, seedCompletedPayment } from "./helpers";
const SS = "../specs/reviews/screenshots/e5-s3/";
const at = "2026-10-04T09:30:00Z";
const pay = (state: string, refund: unknown) => ({
  id: "pay_m", customer_id: "cus_001", amount_paise: 250000, rail: "UPI", beneficiary: "A", state,
  reason_code: null, refund, created_at: at, events: [], attempts: [],
});
let paymentId = "";
test.beforeAll(async ({ request }) => {
  await resetDb(request);
  paymentId = await seedCompletedPayment(request, 250000);
});
test("E5-S3 live COMPLETED no refund shows button", async ({ page }) => {
  await page.goto(`/payments/${paymentId}`);
  await expect(page.getByRole("button", { name: "Request refund" })).toBeVisible();
  await page.screenshot({ path: SS + "01-live-button.png", fullPage: true });
});
test("E5-S3 FAILED hides button; refund states", async ({ page }) => {
  await page.route("http://localhost:8000/payments/pay_m", (r) => r.fulfill({ json: pay("FAILED", null) }));
  await page.goto("/payments/pay_m");
  await expect(page.getByText("FAILED").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Request refund" })).toHaveCount(0);
  await page.screenshot({ path: SS + "02-failed-no-button.png", fullPage: true });
  for (const [i, [st, rc]] of ([["EXECUTED", null], ["REJECTED", "POLICY_VIOLATION"], ["FAILED", "RAIL_ERROR"]] as const).entries()) {
    await page.unroute("http://localhost:8000/payments/pay_m");
    await page.route("http://localhost:8000/payments/pay_m", (r) => r.fulfill({ json: pay("COMPLETED", { id: "rfd_1", state: st, reason_code: rc }) }));
    await page.goto("/payments/pay_m");
    await expect(page.getByText(st, { exact: true }).first()).toBeVisible();
    if (rc) await expect(page.getByText(rc)).toBeVisible();
    await expect(page.getByRole("button", { name: "Request refund" })).toHaveCount(0);
    await page.screenshot({ path: SS + `0${3 + i}-refund-${st}.png`, fullPage: true });
  }
});
test("E5-S3 pending disables button", async ({ page }) => {
  await page.route("http://localhost:8000/payments/pay_m", (r) => r.fulfill({ json: pay("COMPLETED", null) }));
  await page.route("http://localhost:8000/refunds", async (r) => { await new Promise((s) => setTimeout(s, 1500)); await r.fulfill({ status: 201, json: { id: "rfd_1", state: "REQUESTED" } }); });
  await page.goto("/payments/pay_m");
  const btn = page.getByRole("button", { name: "Request refund" });
  await btn.click();
  await expect(page.getByRole("button").filter({ hasText: /refund/i }).first()).toBeDisabled();
  await page.screenshot({ path: SS + "06-pending.png" });
  await expect(page.getByText("Refund requested")).toBeVisible();
  await page.screenshot({ path: SS + "07-requested.png", fullPage: true });
});
