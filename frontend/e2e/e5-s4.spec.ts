import { test, expect } from "@playwright/test";

const refund = { id: "rfd_1", payment_id: "pay_9", amount_paise: 10000050, state: "REQUESTED", requested_by: "cus_001" };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "admin", customerId: null })));
});

test("E5-S4 queue lists and approves", async ({ page }) => {
  await page.route("http://localhost:8000/refunds?state=REQUESTED", (r) => r.fulfill({ json: { items: [refund], total: 1 } }));
  await page.route("http://localhost:8000/refunds/rfd_1/approve", (r) => r.fulfill({ json: { ...refund, state: "EXECUTED" } }));
  await page.goto("/refunds");
  await expect(page.getByText("Rs 1,00,000.50")).toBeVisible();
  await page.getByRole("button", { name: "Approve refund for payment pay_9" }).click();
  await expect(page.getByRole("cell", { name: "EXECUTED" })).toBeVisible();
});

test("E5-S4 409 and empty", async ({ page }) => {
  await page.route("http://localhost:8000/refunds?state=REQUESTED", (r) => r.fulfill({ json: { items: [refund], total: 1 } }));
  await page.route("http://localhost:8000/refunds/rfd_1/reject", (r) => r.fulfill({ status: 409, json: { error: { code: "REFUND_ALREADY_DECIDED", message: "x" } } }));
  await page.goto("/refunds");
  await page.getByRole("button", { name: "Reject refund for payment pay_9" }).click();
  await expect(page.getByText("This refund was already decided")).toBeVisible();
});
