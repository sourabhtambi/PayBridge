import { test, expect } from "@playwright/test";
const SS = "../specs/reviews/screenshots/e3-s3/";
test("E3-S3 live detail", async ({ page }) => {
  await page.goto("/payments/pay_8e8903fc2944");
  await expect(page.locator('[data-state="COMPLETED"]')).toBeVisible();
  await expect(page.getByText("Rs 2,500.00").first()).toBeVisible();
  await expect(page.getByRole("table", { name: "Attempts" })).toBeVisible();
  await page.screenshot({ path: SS + "01-live-detail.png", fullPage: true });
  await page.setViewportSize({ width: 375, height: 800 });
  await page.screenshot({ path: SS + "02-live-375.png", fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
test("E3-S3 live 404, mocked failed, skeleton", async ({ page }) => {
  await page.goto("/payments/pay_nope");
  await expect(page.getByText("Payment not found")).toBeVisible();
  await page.screenshot({ path: SS + "03-404.png" });
  const U = "http://localhost:8000/payments/pay_f";
  const at = "2026-10-04T09:30:00Z";
  await page.route(U, async (r) => { await new Promise((s) => setTimeout(s, 1500)); return r.fulfill({ json: { id: "pay_f", customer_id: "cus_001", amount_paise: 10000050, rail: "IMPS", beneficiary: "A", state: "FAILED", reason_code: "INSUFFICIENT_FUNDS", created_at: at,
    events: [{ id: "e2", type: "PAYMENT_FAILED", payload: {}, at: "2026-10-04T09:32:00Z" }, { id: "e1", type: "PAYMENT_CREATED", payload: {}, at }, { id: "e3", type: "PAYMENT_SUBMITTED", payload: {}, at: "2026-10-04T09:31:00Z" }],
    attempts: [{ attempt_no: 1, outcome: "FAILURE", error_code: "X", at }, { attempt_no: 2, outcome: "FAILURE", error_code: "Y", at }] } }); });
  await page.goto("/payments/pay_f");
  await page.screenshot({ path: SS + "04-skeleton.png" });
  await expect(page.getByText("INSUFFICIENT_FUNDS").first()).toBeVisible();
  await page.screenshot({ path: SS + "05-failed.png", fullPage: true });
  await expect(page.getByRole("table", { name: "Attempts" }).locator("tbody tr")).toHaveCount(2);
});
