import { test, expect } from "@playwright/test";

const SHOTS = "/Users/sourabh/paybridge/specs/reviews/screenshots/e4-s5";
const sim = ["UPI", "IMPS", "NEFT", "RTGS"].map((rail) => ({ rail, mode: "success", reason_code: null, transient_failure_rate: 0 }));
async function asRole(page: import("@playwright/test").Page, role: string) {
  await page.addInitScript((r) => window.localStorage.setItem("paybridge.session", JSON.stringify({ role: r })), role);
}

test("F069 save transient 0.3 PUT body + confirmation; F072 labels and keyboard", async ({ page }) => {
  await asRole(page, "admin");
  let body: unknown = null;
  await page.route("http://localhost:8000/admin/simulation", (r) => r.fulfill({ json: { items: sim } }));
  await page.route("http://localhost:8000/admin/simulation/UPI", (r) => { body = r.request().postDataJSON(); return r.fulfill({ json: sim[0] }); });
  await page.goto("/simulation");
  await expect(page.getByRole("form")).toHaveCount(4);
  await page.screenshot({ path: `${SHOTS}/simulation.png`, fullPage: true });
  // F072 labels
  for (const rail of ["UPI", "IMPS", "NEFT", "RTGS"]) {
    const f = page.getByRole("form", { name: `${rail} simulation` });
    await expect(f.getByRole("radio", { name: "Success", exact: true })).toHaveCount(1);
    await expect(f.getByRole("radio", { name: "Permanent failure", exact: true })).toHaveCount(1);
    await expect(f.getByRole("radio", { name: "Transient", exact: true })).toHaveCount(1);
    await expect(f.getByLabel("Reason code (used for permanent failure)")).toHaveCount(1);
    await expect(f.getByLabel("Transient failure rate (0 to 1)")).toHaveCount(1);
  }
  // keyboard: focus UPI success radio, arrow to permanent, arrow to transient
  const upi = page.getByRole("form", { name: "UPI simulation" });
  await upi.getByRole("radio", { name: "Success", exact: true }).focus();
  await page.keyboard.press("ArrowDown");
  await expect(upi.getByRole("radio", { name: "Permanent failure", exact: true })).toBeChecked();
  await page.keyboard.press("ArrowDown");
  await expect(upi.getByRole("radio", { name: "Transient", exact: true })).toBeChecked();
  await page.keyboard.press("Tab");
  await expect(upi.getByLabel("Reason code (used for permanent failure)")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(upi.getByLabel("Transient failure rate (0 to 1)")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(upi.getByRole("button", { name: "Save UPI" })).toBeFocused();
  await upi.getByLabel("Transient failure rate (0 to 1)").fill("0.3");
  await upi.getByRole("button", { name: "Save UPI" }).click();
  await expect(upi.getByRole("status")).toContainText("Saved");
  expect(body).toEqual({ mode: "transient", reason_code: null, transient_failure_rate: 0.3 });
  await page.screenshot({ path: `${SHOTS}/simulation-saved.png`, fullPage: true });
});

test("F071 stuck empty and 500", async ({ page }) => {
  await asRole(page, "ops");
  await page.route("http://localhost:8000/ops/stuck-payments", (r) => r.fulfill({ json: { items: [{ payment_id: "pay_s1", rail: "NEFT", amount_paise: 250000, age_seconds: 420 }] } }));
  await page.goto("/stuck-payments");
  const t = page.getByRole("table", { name: "Stuck payments" });
  for (const h of ["Payment", "Rail", "Amount", "Age"]) await expect(t.getByRole("columnheader", { name: h })).toBeVisible();
  await expect(t).toContainText("NEFT");
  await expect(t).toContainText("2,500");
  await page.screenshot({ path: `${SHOTS}/stuck-list.png`, fullPage: true });
  await page.unroute("http://localhost:8000/ops/stuck-payments");
  await page.route("http://localhost:8000/ops/stuck-payments", (r) => r.fulfill({ json: { items: [] } }));
  await page.goto("/stuck-payments");
  await expect(page.getByText("No stuck payments").first()).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/stuck-empty.png`, fullPage: true });
  await page.unroute("http://localhost:8000/ops/stuck-payments");
  await page.route("http://localhost:8000/ops/stuck-payments", (r) => r.fulfill({ status: 500, json: { detail: "boom" } }));
  await page.goto("/stuck-payments");
  await expect(page.getByRole("button", { name: /retry/i })).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/stuck-error.png`, fullPage: true });
});
