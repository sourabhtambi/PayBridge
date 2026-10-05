import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";
import type { APIRequestContext, Page } from "@playwright/test";

const API = "http://localhost:8000";
const cust = { "X-Role": "customer", "X-Customer-Id": "cus_001" };
const ops = { "X-Role": "ops" };
const seed = (role: string, customerId: string | null) => ({ role, customerId });

async function completedPayment(request: APIRequestContext): Promise<string> {
  const res = await request.post(`${API}/payments`, {
    headers: { ...cust, "Idempotency-Key": `e9s3-${Date.now()}-${Math.random()}` },
    data: { amount_paise: 123400, beneficiary: "E9S3 Axe" },
  });
  expect(res.status()).toBeLessThan(300);
  const id = (await res.json()).id as string;
  await expect.poll(async () => (await (await request.get(`${API}/payments/${id}`, { headers: cust })).json()).state, { timeout: 30000 }).toBe("COMPLETED");
  return id;
}

async function login(page: Page, role: string, customerId: string | null): Promise<void> {
  await page.addInitScript((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), seed(role, customerId));
}

async function expectNoSeriousViolations(page: Page): Promise<void> {
  const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const bad = violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
}

test.describe("F135 axe-core on every screen", () => {
  let paymentId = "";
  test.beforeAll(async ({ request }) => {
    paymentId = await completedPayment(request);
    const rr = await request.post(`${API}/refunds`, { headers: cust, data: { payment_id: paymentId } });
    expect([201, 409]).toContain(rr.status());
    const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
    const run = await request.post(`${API}/reconciliation/run`, { headers: ops, data: { statement_date: today } });
    expect(run.status()).toBeLessThan(300);
  });

  test("customer screens", async ({ page }) => {
    await login(page, "customer", "cus_001");
    await page.goto("/payments");
    await expect(page.getByRole("heading", { name: "My payments" })).toBeVisible();
    await expect(page.locator(`tr[data-id="${paymentId}"]`)).toBeVisible();
    await expectNoSeriousViolations(page);

    await page.goto("/payments/new");
    await page.getByLabel("Amount (Rs)").fill("abc");
    await expect(page.locator(".field-error").first()).toBeVisible();
    await expectNoSeriousViolations(page);

    await page.goto(`/payments/${paymentId}`);
    await expect(page.locator("[data-refund]")).toBeVisible();
    await expect(page.getByText("Refund", { exact: false }).first()).toBeVisible();
    await expectNoSeriousViolations(page);
  });

  test("ops screens", async ({ page }) => {
    await login(page, "ops", null);
    // The backend's statement generator yields no unresolved rows for today, so serve one
    // contract-shaped unmatched row (same shape as GET /reconciliation/unmatched) to open the dialog.
    await page.route(`${API}/reconciliation/unmatched*`, (route) => route.fulfill({
      json: { total: 1, items: [{ id: "rr_e9s3", rail: "UPI", status: "amount_mismatch", payment_amount_paise: 123400, statement_amount_paise: 123000 }] },
    }));
    await page.goto("/reconciliation");
    await expect(page.getByRole("button", { name: "Resolve" }).first()).toBeVisible();
    await expectNoSeriousViolations(page);
    await page.getByRole("button", { name: "Resolve" }).first().click();
    await expect(page.getByRole("dialog", { name: "Resolve result" })).toBeVisible();
    await expectNoSeriousViolations(page);

    await page.goto("/stuck-payments");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expectNoSeriousViolations(page);
  });

  test("admin screens", async ({ page }) => {
    await login(page, "admin", null);
    for (const [route, heading] of [["/dashboard", "Dashboard"], ["/settlement", "Settlement"], ["/simulation", "Simulation"], ["/refunds", "Refund queue"]] as const) {
      await page.goto(route);
      await expect(page.getByRole("heading", { level: 1 })).toContainText(heading);
      await expect(page.getByRole("progressbar")).toHaveCount(0);
      await page.waitForLoadState("networkidle");
      await expectNoSeriousViolations(page);
    }
    await page.goto("/refunds");
    await expect(page.locator("tbody tr[data-id]").first()).toBeVisible();
    await expectNoSeriousViolations(page);
  });
});

test("F136 keyboard-only create payment and open detail", async ({ page }) => {
  await login(page, "customer", "cus_001");
  await page.goto("/payments/new");
  const pressUntilFocused = async (name: string | RegExp) => {
    for (let i = 0; i < 30; i++) {
      const label = await page.evaluate(() => {
        const e = document.activeElement as HTMLElement | null;
        return e?.id === "amount" ? "Amount (Rs)" : e?.id === "beneficiary" ? "Beneficiary" : (e?.textContent ?? "").trim();
      });
      if (typeof name === "string" ? label === name : name.test(label)) return;
      await page.keyboard.press("Tab");
    }
    throw new Error(`never focused ${String(name)}`);
  };
  await pressUntilFocused("Amount (Rs)");
  await page.keyboard.type("1500");
  await page.keyboard.press("Tab");
  expect(await page.evaluate(() => document.activeElement?.id)).toBe("beneficiary");
  await page.keyboard.type("Keyboard Only");
  await pressUntilFocused("Pay");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/payments\/(?!new$)[A-Za-z0-9_-]+$/);
  const id = page.url().split("/").pop() as string;
  expect(id).not.toBe("new");
  await expect(page.getByText(id).first()).toBeVisible();

  // back to the list and open the detail by keyboard Enter on the link
  await page.goto("/payments");
  const link = page.locator(`a[href="/payments/${id}"]`);
  await expect(link).toBeVisible();
  for (let i = 0; i < 40; i++) {
    if (await link.evaluate((e) => e === document.activeElement)) break;
    await page.keyboard.press("Tab");
  }
  await expect(link).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`/payments/${id}$`));
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("F138 status elements carry text labels", async ({ page, request }) => {
  const id = await completedPayment(request);
  await request.post(`${API}/refunds`, { headers: cust, data: { payment_id: id } });
  await login(page, "customer", "cus_001");
  await page.goto("/payments");
  const badges = page.locator(`tr[data-id="${id}"] [data-state]`);
  await expect(badges).toHaveText(/COMPLETED/);
  for (const el of await page.locator("[data-state]").all()) expect((await el.innerText()).trim()).not.toBe("");
  await page.goto(`/payments/${id}`);
  await expect(page.locator("[data-refund]")).toHaveText(/\S/);

  await login(page, "admin", null);
  await page.goto("/dashboard");
  for (const s of ["CREATED", "SUBMITTED", "COMPLETED", "FAILED"]) await expect(page.locator(`[data-status="${s}"]`)).toContainText(s);
  for (const r of ["UPI", "IMPS", "NEFT", "RTGS"]) await expect(page.locator(`[data-rail="${r}"]`)).toContainText(r);
});
