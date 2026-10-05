import { test, expect } from "@playwright/test";

const API = "http://localhost:8000/payments**";
const SS = "../specs/reviews/screenshots/e3-s2/";
const item = (id: string, state: string, reason: string | null) => ({
  id, customer_id: "cus_001", amount_paise: 10000050, rail: "IMPS", beneficiary: "A",
  state, reason_code: reason, created_at: "2026-10-04T09:30:00Z",
});

test("E3-S2 list states", async ({ page }) => {
  const items = [item("pay_1", "CREATED", null), item("pay_2", "SUBMITTED", null), item("pay_3", "COMPLETED", null), item("pay_4", "FAILED", "INSUFFICIENT_FUNDS")];
  await page.route(API, (r) => r.fulfill({ json: { items, total: 4 } }));
  await page.goto("/payments");
  await expect(page.getByRole("table", { name: "My payments" })).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(4);
  for (const s of ["CREATED", "SUBMITTED", "COMPLETED", "FAILED"]) await expect(page.locator(`[data-state="${s}"]`)).toHaveText(new RegExp(s));
  await expect(page.getByText("Rs 1,00,000.50").first()).toBeVisible();
  await expect(page.getByText("INSUFFICIENT_FUNDS")).toHaveCount(1);
  await expect(page.getByRole("link", { name: "pay_3" })).toHaveAttribute("href", "/payments/pay_3");
  await page.screenshot({ path: SS + "01-list.png" });
  await page.getByRole("link", { name: "pay_1" }).focus();
  await expect(page.getByRole("link", { name: "pay_1" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "pay_2" })).toBeFocused();
});

test("E3-S2 empty and error retry", async ({ page }) => {
  await page.route(API, (r) => r.fulfill({ json: { items: [], total: 0 } }));
  await page.goto("/payments");
  await expect(page.getByText("No payments yet")).toBeVisible();
  await expect(page.getByRole("link", { name: "Create your first payment" })).toHaveAttribute("href", "/payments/new");
  await page.screenshot({ path: SS + "02-empty.png" });
  await page.unroute(API);
  let healthy = false;
  await page.route(API, (r) => (!healthy ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: { items: [item("pay_9", "COMPLETED", null)], total: 1 } })));
  await page.reload();
  await expect(page.getByRole("alert")).toContainText("Request failed: 500");
  await page.screenshot({ path: SS + "03-error.png" });
  healthy = true;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByRole("link", { name: "pay_9" })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});
