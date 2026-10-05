import { test, expect } from "@playwright/test";

const at = "2026-10-04T09:30:00Z";
const pay = (refund: unknown) => ({
  id: "pay_r1", customer_id: "cus_001", amount_paise: 250000, rail: "UPI", beneficiary: "A", state: "COMPLETED",
  reason_code: null, refund, created_at: at, events: [], attempts: [],
});

test("E5-S3 request refund, then 409 message", async ({ page }) => {
  await page.route("http://localhost:8000/payments/pay_r1", (r) => r.fulfill({ json: pay(null) }));
  await page.route("http://localhost:8000/refunds", (r) => r.fulfill({ status: 201, json: { id: "rfd_1", state: "REQUESTED" } }));
  await page.goto("/payments/pay_r1");
  const btn = page.getByRole("button", { name: "Request refund" });
  await expect(btn).toBeVisible();
  await btn.click();
  await expect(page.getByText("Refund requested")).toBeVisible();
  await expect(btn).toHaveCount(0);
});

test("E5-S3 409 shows message", async ({ page }) => {
  await page.route("http://localhost:8000/payments/pay_r1", (r) => r.fulfill({ json: pay(null) }));
  await page.route("http://localhost:8000/refunds", (r) => r.fulfill({ status: 409, json: { error: { code: "REFUND_ALREADY_EXISTS", message: "x" } } }));
  await page.goto("/payments/pay_r1");
  await page.getByRole("button", { name: "Request refund" }).click();
  await expect(page.getByText("A refund was already requested for this payment")).toBeVisible();
});

test("E5-S3 rejected shows reason code", async ({ page }) => {
  await page.route("http://localhost:8000/payments/pay_r1", (r) => r.fulfill({ json: pay({ id: "rfd_1", state: "REJECTED", reason_code: "POLICY_VIOLATION" }) }));
  await page.goto("/payments/pay_r1");
  await expect(page.getByText("REJECTED")).toBeVisible();
  await expect(page.getByText("POLICY_VIOLATION")).toBeVisible();
  await expect(page.getByRole("button", { name: "Request refund" })).toHaveCount(0);
});
