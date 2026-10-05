import { test, expect, Page } from "@playwright/test";
const SS = "../specs/reviews/screenshots/e3-s1/";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const amt = (p: Page) => p.getByLabel("Amount (Rs)");
const rail = (p: Page) => p.getByTestId("rail-preview");

test("E3-S1 end to end", async ({ page }) => {
  const reqs: { key: string; body: any }[] = [];
  page.on("request", (r) => { if (r.method() === "POST" && r.url().includes("/payments")) reqs.push({ key: r.headers()["idempotency-key"], body: r.postDataJSON() }); });
  await page.goto("/payments/new");
  await expect(amt(page)).toBeVisible();
  await expect(page.getByLabel("Beneficiary")).toBeVisible();
  const key1 = await page.getByLabel("Idempotency key").inputValue();
  expect(key1).toMatch(UUID);
  await page.screenshot({ path: SS + "01-form.png" });

  // F039
  const cases: [string, string][] = [["1,00,000", "UPI"], ["100000.50", "IMPS"], ["200000.01", "NEFT"], ["500000.01", "RTGS"]];
  for (const [a, r] of cases) { await amt(page).fill(a); await expect(rail(page)).toHaveAttribute("data-rail", r); await expect(rail(page)).toContainText(r); }
  await page.screenshot({ path: SS + "02-rail-rtgs.png" });
  await amt(page).fill("0.99"); await expect(rail(page)).toHaveAttribute("data-rail", "none");
  await expect(rail(page)).not.toContainText(/UPI|IMPS|NEFT|RTGS/);

  // F040 client side
  for (const v of ["0", "-5"]) { await amt(page).fill(v); await expect(page.locator("#amount-err")).not.toBeEmpty(); }
  await page.screenshot({ path: SS + "03-client-error.png" });

  // F040 422 mock, F041 409 mock
  await page.route("**/payments", (route) => route.request().method() === "POST" ? route.fulfill({ status: 422, contentType: "application/json", body: "{}" }) : route.continue());
  await amt(page).fill("5"); await page.getByLabel("Beneficiary").fill("Acme");
  await page.getByRole("button", { name: "Pay" }).click();
  await expect(page.locator("#amount-err")).toHaveText("Amount must be at least Rs 1");
  await page.screenshot({ path: SS + "04-422.png" });
  await page.unroute("**/payments");
  await page.route("**/payments", (route) => route.request().method() === "POST" ? route.fulfill({ status: 409, contentType: "application/json", body: "{}" }) : route.continue());
  await page.getByRole("button", { name: "Pay" }).click();
  await expect(page.getByText("This request was already submitted with different details. Start a new payment.")).toBeVisible();
  await page.screenshot({ path: SS + "05-409.png" });

  // F041 200 replay
  await page.unroute("**/payments");
  await page.route("**/payments", (route) => route.request().method() === "POST" ? route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*", "access-control-expose-headers": "*" }, body: JSON.stringify({ id: "pay_mock" }) }) : route.continue());
  await page.getByRole("button", { name: "Pay" }).click();
  await expect(page).toHaveURL(/\/payments\/pay_mock$/);
  await expect(page.getByText("This payment was already created. Showing the original.")).toBeVisible();
  await page.screenshot({ path: SS + "06-200.png" });
  await page.unroute("**/payments");

  // F042 / F038 / F041 202 live backend with pending state
  await page.goto("/payments/new");
  await amt(page).fill("1,00,000.50"); await page.getByLabel("Beneficiary").fill("Acme Ltd");
  const key2 = await page.getByLabel("Idempotency key").inputValue();
  await page.route("**/payments", async (route) => { if (route.request().method() === "POST") await new Promise((r) => setTimeout(r, 1200)); await route.continue(); });
  await page.getByRole("button", { name: "Pay" }).click();
  const btn = page.getByRole("button", { name: /Submitting/ });
  await expect(btn).toBeDisabled();
  await page.screenshot({ path: SS + "07-pending.png" });
  await expect(page).toHaveURL(/\/payments\/(?!new)[^/]+$/, { timeout: 10000 });
  const last = reqs[reqs.length - 1];
  expect(last.key).toBe(key2); expect(last.key).toMatch(UUID);
  expect(last.body.amount_paise).toBe(10000050);
  expect(Number.isInteger(last.body.amount_paise)).toBe(true);
  console.log("LIVE URL", page.url(), JSON.stringify(last));
  await page.screenshot({ path: SS + "08-202.png" });
  // key regeneration: new form session after success (SPA nav back)
  await page.unroute("**/payments");
  await page.goBack();
  await expect(page.getByLabel("Idempotency key")).toBeVisible();
  console.log("KEY after back", await page.getByLabel("Idempotency key").inputValue(), "was", key2);
});
