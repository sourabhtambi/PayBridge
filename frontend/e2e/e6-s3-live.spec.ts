import { test, expect } from "@playwright/test";
import { execSync } from "node:child_process";

const API = "http://localhost:8000";
const SS = "../specs/reviews/screenshots/e6-s3/";
const DB = "../backend/data/paybridge.db";
const cust = { "X-Role": "customer", "X-Customer-Id": "cus_001" };
const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });

test("E6-S3 live run and resolve", async ({ page, request }) => {
  const res = await request.post(`${API}/payments`, {
    headers: { ...cust, "Idempotency-Key": `e6s3-${Date.now()}` },
    data: { amount_paise: 777700, beneficiary: "E6S3 Live" },
  });
  expect(res.status()).toBeLessThan(300);
  const id = (await res.json()).id as string;
  let ref = "";
  for (let i = 0; i < 40; i++) {
    const p = await (await request.get(`${API}/payments/${id}`, { headers: cust })).json();
    if (p.state === "COMPLETED") { ref = p.rail_reference ?? ""; break; }
    await new Promise((s) => setTimeout(s, 500));
  }
  expect(ref).not.toBe("");
  const rail = execSync(`sqlite3 ${DB} "select rail from payments where id='${id}'"`).toString().trim();
  const completed = execSync(`sqlite3 ${DB} "select completed_at from payments where id='${id}'"`).toString().trim();
  // seed one orphan external entry for today
  execSync(`sqlite3 ${DB} "insert into rail_statement_entries(id,rail,payment_ref,payment_id,amount_paise,statement_date,created_at) values ('rse_e6s3orphan${Date.now()}','${rail}','ORPHAN-${Date.now()}',NULL,4242,'${today}','${completed}')"`);

  await page.addInitScript(() => window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "ops", customerId: null })));
  await page.goto("/reconciliation");
  await expect(page.getByRole("navigation").getByRole("link")).toHaveText(["Reconciliation", "Stuck payments"]);
  await page.screenshot({ path: SS + "10-live-before.png", fullPage: true });
  await page.getByLabel("Statement date").fill(today);
  await page.getByRole("button", { name: "Run reconciliation" }).click();
  await expect(page.getByLabel("Run summary")).toBeVisible();
  await page.screenshot({ path: SS + "11-live-run.png", fullPage: true });
  await expect(page.getByText("unmatched_external", { exact: true }).first()).toBeVisible();
  const before = await page.getByRole("button", { name: "Resolve" }).count();
  expect(before).toBeGreaterThan(0);
  const trigger = page.getByRole("button", { name: "Resolve" }).first();
  await trigger.click();
  await page.getByRole("button", { name: "Resolve", exact: true }).last().click();
  await expect(page.getByText("A note is required")).toBeVisible();
  await page.screenshot({ path: SS + "12-live-dialog-error.png", fullPage: true });
  await page.getByLabel("Resolution note").fill("live check");
  await page.getByRole("button", { name: "Resolve", exact: true }).last().click();
  await expect(page.getByRole("button", { name: "Resolve" })).toHaveCount(before - 1);
  await page.screenshot({ path: SS + "13-live-resolved.png", fullPage: true });
  const un = await (await request.get(`${API}/reconciliation/unmatched`, { headers: { "X-Role": "ops" } })).json();
  expect(un.total).toBe(before - 1);
});

test("E6-S3 mocked states and focus", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "ops", customerId: null })));
  const U = "http://localhost:8000/reconciliation/unmatched";
  await page.route(U, async (r) => { await new Promise((s) => setTimeout(s, 3000)); await r.fulfill({ json: { items: [], total: 0 } }); });
  await page.goto("/reconciliation");
  await page.screenshot({ path: SS + "20-loading.png", fullPage: true });
  await expect(page.getByTestId("skeleton-row").first()).toBeAttached();
  expect(await page.locator("[data-testid=skeleton-row] .skel").count()).toBeGreaterThan(0);
  await expect(page.getByText("Nothing to reconcile")).toBeVisible();
  await page.screenshot({ path: SS + "21-empty.png", fullPage: true });
  await page.unroute(U);
  await page.route(U, (r) => r.fulfill({ status: 500, json: { error: { code: "X", message: "x" } } }));
  await page.goto("/reconciliation");
  await expect(page.getByRole("alert").filter({ hasText: "Something went wrong" })).toBeVisible();
  await expect(page.getByRole("button", { name: /retry/i })).toBeVisible();
  await page.screenshot({ path: SS + "22-error.png", fullPage: true });
  await page.unroute(U);
  const rows = [{ id: "rr_1", rail: "UPI", status: "unmatched_internal", payment_amount_paise: 10000, statement_amount_paise: null }];
  await page.route(U, (r) => r.fulfill({ json: { items: rows, total: 1 } }));
  await page.goto("/reconciliation");
  const trigger = page.locator("table").getByRole("button", { name: "Resolve" }).first();
  await trigger.focus();
  await trigger.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.screenshot({ path: SS + "23-dialog.png", fullPage: true });
  for (let i = 0; i < 8; i++) {
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => !!document.activeElement?.closest("[role=dialog]"))).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(trigger).toBeFocused();
});
