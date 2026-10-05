import { test, expect } from "@playwright/test";

const sim = ["UPI", "IMPS", "NEFT", "RTGS"].map((rail) => ({ rail, mode: "success", reason_code: null, transient_failure_rate: 0 }));

async function asRole(page: import("@playwright/test").Page, role: string) {
  await page.addInitScript((r) => window.localStorage.setItem("paybridge.session", JSON.stringify({ role: r })), role);
}

test("E4-S5 simulation: invalid rate blocked, keyboard save confirms", async ({ page }) => {
  await asRole(page, "admin");
  let puts = 0;
  await page.route("http://localhost:8000/admin/simulation", (r) => r.fulfill({ json: { items: sim } }));
  await page.route("http://localhost:8000/admin/simulation/UPI", (r) => { puts++; return r.fulfill({ json: sim[0] }); });
  await page.goto("/simulation");
  await expect(page.getByRole("form")).toHaveCount(4);
  const rate = page.getByLabel("Transient failure rate (0 to 1)").first();
  await rate.fill("2");
  await page.getByRole("button", { name: "Save UPI" }).click();
  await expect(page.getByText("Enter a rate between 0 and 1")).toBeVisible();
  expect(puts).toBe(0);
  await rate.fill("0.5");
  await page.getByRole("button", { name: "Save UPI" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toContainText("Saved");
  expect(puts).toBe(1);
});

test("E4-S5 stuck payments list and empty", async ({ page }) => {
  await asRole(page, "ops");
  await page.route("http://localhost:8000/ops/stuck-payments", (r) =>
    r.fulfill({ json: { items: [{ payment_id: "pay_s1", rail: "NEFT", amount_paise: 250000, age_seconds: 420 }] } }));
  await page.goto("/stuck-payments");
  await expect(page.getByRole("table", { name: "Stuck payments" })).toContainText("pay_s1");
  await expect(page.getByRole("table", { name: "Stuck payments" })).toContainText("7m");
});
