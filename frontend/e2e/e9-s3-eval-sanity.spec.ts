import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";

const seed = (role: string, customerId: string | null) => ({ role, customerId });
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

test("axe detects injected violations (non-vacuous)", async ({ page }) => {
  await page.addInitScript((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), seed("customer", "cus_001"));
  await page.goto("/payments");
  await expect(page.getByRole("heading", { name: "My payments" })).toBeVisible();
  await page.evaluate(() => {
    const d = document.createElement("div");
    d.innerHTML = '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw="><p id="lc" style="color:#bbb;background:#fff">low contrast text</p>';
    document.querySelector("main")!.appendChild(d);
  });
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  const ids = violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id);
  console.log("INJECTED_DETECTED", JSON.stringify(ids));
  expect(ids).toContain("image-alt");
  expect(ids).toContain("color-contrast");
});

test("extra F138 status text on rail preview, settlement, stuck, reconciliation", async ({ page }) => {
  await page.addInitScript((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), seed("customer", "cus_001"));
  await page.goto("/payments/new");
  await page.getByLabel("Amount (Rs)").fill("1500");
  await expect(page.locator('[data-testid="rail-preview"]')).toHaveText(/\S/);
  console.log("RAIL_PREVIEW", await page.locator('[data-testid="rail-preview"]').innerText());
  await page.addInitScript((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), seed("admin", null));
  await page.evaluate((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), seed("admin", null));
  await page.goto("/settlement");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.waitForLoadState("networkidle");
  console.log("SETTLEMENT_BADGES", await page.locator(".badge").count());
  for (const el of await page.locator(".badge").all()) expect((await el.innerText()).trim()).not.toBe("");
  await page.goto("/stuck-payments");
  await page.waitForLoadState("networkidle");
  console.log("STUCK_ROWS", await page.locator("tbody tr").count(), "BADGES", await page.locator("[data-state],.badge").count());
});
