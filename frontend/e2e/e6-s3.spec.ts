import { test, expect } from "@playwright/test";

const row = { id: "rr_1", rail: "UPI", status: "amount_mismatch", payment_amount_paise: 10000, statement_amount_paise: 9000 };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "ops", customerId: null })));
});

test("E6-S3 ops nav, run, resolve", async ({ page }) => {
  await page.route("http://localhost:8000/reconciliation/unmatched", (r) => r.fulfill({ json: { items: [row], total: 1 } }));
  await page.route("http://localhost:8000/reconciliation/run", (r) =>
    r.fulfill({ json: { statement_date: "2026-10-04", counts: { matched: 4, unmatched_internal: 0, unmatched_external: 0, amount_mismatch: 1 } } }));
  await page.route("http://localhost:8000/reconciliation/rr_1/resolve", (r) => r.fulfill({ json: { ...row, resolved: true } }));
  await page.goto("/reconciliation");
  await expect(page.getByRole("navigation").getByRole("link")).toHaveText(["Reconciliation", "Stuck payments"]);
  await expect(page.getByText("amount_mismatch", { exact: true }).first()).toBeVisible();
  await page.getByLabel("Statement date").fill("2026-10-04");
  await page.getByRole("button", { name: "Run reconciliation" }).click();
  await expect(page.getByLabel("Run summary")).toBeVisible();
  await page.getByRole("button", { name: "Resolve" }).click();
  await page.getByRole("button", { name: "Resolve", exact: true }).last().click();
  await expect(page.getByText("A note is required")).toBeVisible();
  await page.getByLabel("Resolution note").fill("checked");
  await page.getByRole("button", { name: "Resolve", exact: true }).last().click();
  await expect(page.getByText("Nothing to reconcile")).toBeVisible();
});
