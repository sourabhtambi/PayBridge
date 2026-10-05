import { expect, test } from "@playwright/test";

const refund = { id: "rfd_1", payment_id: "pay_1", amount_paise: 250000, state: "REQUESTED", requested_by: "cus_001" };
const summary = {
  date: "2026-10-04",
  rails: ["UPI", "IMPS", "NEFT", "RTGS"].map((rail) => ({ rail, payment_count: 1, total_paise: 10000050 })),
  status_counts: { CREATED: 1, SUBMITTED: 0, COMPLETED: 2, FAILED: 1 },
  pending_refunds: [refund],
  settlement_files: [],
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "admin", customer_id: null })));
  await page.route("http://localhost:8000/dashboard/summary?*", (r) => r.fulfill({ json: summary }));
  await page.route("http://localhost:8000/refunds/rfd_1/approve", (r) => r.fulfill({ json: { ...refund, state: "EXECUTED" } }));
  await page.route("http://localhost:8000/refunds?state=REQUESTED", (r) => r.fulfill({ json: { items: [], total: 0 } }));
});

test("dashboard tiles, nav and refund link", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("navigation").getByRole("link")).toHaveText(["Dashboard", "Settlement", "Simulation"]);
  await expect(page.locator('[data-rail="UPI"]')).toContainText("Rs 1,00,000.50");
  await expect(page.locator('[data-status="COMPLETED"]')).toContainText("2");
  await page.getByRole("button", { name: "Approve refund for payment pay_1" }).click();
  await expect(page.getByText("EXECUTED")).toBeVisible();
  await expect(page.getByText("0 pending")).toBeVisible();
  await page.getByRole("link", { name: "Open full refund queue" }).click();
  await expect(page.getByRole("heading", { name: "Refund queue" })).toBeVisible();
});

test("tile error retries independently", async ({ page }) => {
  await page.route("http://localhost:8000/dashboard/summary?*", (r) => r.fulfill({ json: { ...summary, rails: undefined } }));
  await page.goto("/dashboard");
  await expect(page.getByRole("button", { name: "Retry" })).toHaveCount(1);
});
