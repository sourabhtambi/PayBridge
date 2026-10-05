import { test, expect } from "@playwright/test";
import { resetDb, seedCompletedPayment } from "./helpers";
const SS = "../specs/reviews/screenshots/e3-s2/";
let ids: string[] = [];
test.beforeAll(async ({ request }) => {
  await resetDb(request);
  ids = [];
  for (const paise of [10000050, 10000050, 50000000, 250000, 150000]) ids.push(await seedCompletedPayment(request, paise));
});
test("E3-S2 live list", async ({ page }) => {
  await page.goto("/payments");
  await expect(page.getByRole("table", { name: "My payments" })).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(5);
  await expect(page.getByText("Rs 1,00,000.50").first()).toBeVisible();
  await expect(page.getByText("Rs 5,00,000.00")).toBeVisible();
  await expect(page.getByText("Rs 2,500.00")).toBeVisible();
  await expect(page.getByRole("link", { name: "pay_f1c397308fa6" })).toHaveCount(0);
  await expect(page.getByText("7,777.00")).toHaveCount(0);
  await expect(page.locator('[data-state="COMPLETED"]')).toHaveCount(5);
  await page.screenshot({ path: SS + "04-live.png" });
  await page.keyboard.press("Tab"); 
  const link = page.getByRole("link", { name: ids[0] });
  await link.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`/payments/${ids[0]}$`));
});

const API = "http://localhost:8000/payments**";
const item = (id: string, state: string, reason: string | null) => ({
  id, customer_id: "cus_001", amount_paise: 10000050, rail: "IMPS", beneficiary: "A",
  state, reason_code: reason, created_at: "2026-10-04T09:30:00Z",
});
test("E3-S2 mocked states (API-only route)", async ({ page }) => {
  const items = [item("pay_1", "CREATED", null), item("pay_2", "SUBMITTED", null), item("pay_3", "COMPLETED", null), item("pay_4", "FAILED", "INSUFFICIENT_FUNDS")];
  await page.route(API, (r) => r.fulfill({ json: { items, total: 4 } }));
  await page.goto("/payments");
  await expect(page.locator("tbody tr")).toHaveCount(4);
  for (const s of ["CREATED", "SUBMITTED", "COMPLETED", "FAILED"]) await expect(page.locator(`[data-state="${s}"]`)).toHaveText(new RegExp(s));
  await expect(page.getByText("INSUFFICIENT_FUNDS")).toHaveCount(1);
  await expect(page.locator("caption")).toHaveCount(1);
  await page.screenshot({ path: SS + "01-list.png" });
  await page.getByRole("link", { name: "pay_1" }).focus();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "pay_2" })).toBeFocused();
  await page.unroute(API);
  await page.route(API, (r) => r.fulfill({ json: { items: [], total: 0 } }));
  await page.reload();
  await expect(page.getByText("No payments yet")).toBeVisible();
  await expect(page.getByRole("link", { name: "Create your first payment" })).toHaveAttribute("href", "/payments/new");
  await page.screenshot({ path: SS + "02-empty.png" });
  await page.unroute(API);
  let n = 0;
  await page.route(API, (r) => (r.request().method() !== "GET" ? r.fulfill({ status: 204 }) : n === 0 ? r.fulfill({ status: 500, json: {} }) : r.fulfill({ json: { items: [item("pay_9", "COMPLETED", null)], total: 1 } })));
  await page.reload();
  await expect(page.getByRole("alert")).toContainText("Request failed: 500");
  await page.screenshot({ path: SS + "03-error.png" });
  n = 1;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByRole("link", { name: "pay_9" })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.unroute(API);
  await page.route(API, async (r) => { await new Promise((res) => setTimeout(res, 3000)); await r.fulfill({ json: { items: [], total: 0 } }).catch(() => {}); });
  await page.reload();
  await page.screenshot({ path: SS + "05-loading.png" });
  const skel = await page.locator('[class*="skeleton" i], [data-testid*="skeleton" i], [aria-busy="true"]').count();
  expect(skel).toBeGreaterThan(0);
});
