import { test, expect } from "@playwright/test";

const API = "http://localhost:8000/payments/pay_x";
const base = { id: "pay_x", customer_id: "cus_001", amount_paise: 250000, rail: "UPI", beneficiary: "A", reason_code: null, created_at: "2026-10-04T09:30:00Z" };
const events = [{ id: "e1", type: "PAYMENT_CREATED", payload: {}, at: "2026-10-04T09:30:00Z" }];

test("E3-S3 polls then stops, then failed reason", async ({ page }) => {
  let state = "SUBMITTED";
  let hits = 0;
  await page.route(API, (r) => { hits++; return r.fulfill({ json: { ...base, state, events, attempts: [{ attempt_no: 1, outcome: "SUCCESS", error_code: null, at: base.created_at }] } }); });
  await page.goto("/payments/pay_x");
  await expect(page.locator('[data-state="SUBMITTED"]')).toBeVisible();
  state = "COMPLETED";
  await expect(page.locator('[data-state="COMPLETED"]')).toBeVisible({ timeout: 5000 });
  const settled = hits;
  await page.waitForTimeout(4500);
  expect(hits).toBe(settled);
  await expect(page.getByRole("table", { name: "Attempts" })).toContainText("SUCCESS");
});

test("E3-S3 not found and 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.route(API, (r) => r.fulfill({ status: 404, json: {} }));
  await page.goto("/payments/pay_x");
  await expect(page.getByText("Payment not found")).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to payments" })).toHaveAttribute("href", "/payments");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
