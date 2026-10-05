import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const API = "http://localhost:8000";
const SS = "../specs/reviews/screenshots/e7-s3/";
const adminH = { "X-Role": "admin" };
const cust = { "X-Role": "customer", "X-Customer-Id": "cus_001" };
const session = (role: string, customerId: string | null) => ({ role, customerId });
const REPEAT = "Primary file for this date already exists. Late entries were written to a follow-up file.";

test("E7-S3 live run, list, download", async ({ page, request }) => {
  const res = await request.post(`${API}/payments`, {
    headers: { ...cust, "Idempotency-Key": `e7s3-${Date.now()}` },
    data: { amount_paise: 888800, beneficiary: "E7S3 Live" },
  });
  expect(res.status()).toBeLessThan(300);
  const id = (await res.json()).id as string;
  let done = false;
  for (let i = 0; i < 40 && !done; i++) {
    const p = await (await request.get(`${API}/payments/${id}`, { headers: cust })).json();
    done = p.state === "COMPLETED";
    if (!done) await new Promise((s) => setTimeout(s, 500));
  }
  expect(done).toBe(true);

  await page.addInitScript((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), session("admin", null));
  await page.goto("/settlement");
  await expect(page.getByRole("navigation").getByRole("link")).toHaveText(["Dashboard", "Settlement", "Simulation"]);
  await expect(page.getByRole("heading", { name: "Settlement" })).toBeVisible();
  await page.screenshot({ path: SS + "10-live-before.png", fullPage: true });

  const postP = page.waitForRequest((r) => r.url() === `${API}/settlement/run` && r.method() === "POST");
  await page.getByRole("button", { name: "Run now" }).click();
  const posted = await postP;
  expect(posted.headers()["x-role"]).toBe("admin");
  const status = page.getByRole("status");
  await expect(status).toBeVisible();
  const msg = (await status.textContent()) ?? "";
  expect(msg.length).toBeGreaterThan(0);
  await expect(page.locator("table.data tbody tr").first()).toBeVisible();
  await page.screenshot({ path: SS + "11-live-run.png", fullPage: true });

  const items = (await (await request.get(`${API}/settlement/files`, { headers: adminH })).json()).items as
    { id: string; business_date: string; kind: string; row_count: number; checksum: string }[];
  expect(items.length).toBeGreaterThan(0);
  const f = items[items.length - 1];
  const rows = page.locator("table.data tbody tr");
  await expect(rows).toHaveCount(items.length);
  const row = page.locator(`tr[data-id="${f.id}"]`);
  await expect(row).toContainText(f.business_date);
  await expect(row).toContainText(f.kind);
  await expect(row).toContainText(String(f.row_count));
  await expect(row).toContainText(f.checksum);
  const link = row.getByRole("link", { name: `Download CSV: ${f.kind} settlement file for ${f.business_date}` });
  await expect(link).toBeVisible();
  const dl = page.waitForEvent("download");
  await link.click();
  const download = await dl;
  expect(download.suggestedFilename()).toBe(`${f.business_date}-${f.kind}.csv`);
  const csv = readFileSync(await download.path(), "utf8");
  expect(csv).toMatch(/^payment_id,rail,amount_paise,rail_ref,recon_status,unmatched_flag/);
  expect(csv).toContain(`# row_count=${f.row_count}`);
  expect(csv).toContain(`# sha256=${f.checksum}`);
  await page.screenshot({ path: SS + "12-live-downloaded.png", fullPage: true });
  console.log("LIVE_MSG", msg, "KIND", f.kind);
});

test("E7-S3 mocked states", async ({ page }) => {
  await page.addInitScript((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), session("admin", null));
  const L = `${API}/settlement/files`;
  // loading
  await page.route(L, async (r) => { await new Promise((s) => setTimeout(s, 3000)); await r.fulfill({ json: { items: [], total: 0 } }); });
  await page.goto("/settlement");
  await expect(page.getByTestId("skeleton-row").first()).toBeAttached();
  await page.screenshot({ path: SS + "20-loading.png", fullPage: true });
  await expect(page.getByText("No settlement files yet")).toBeVisible();
  await page.screenshot({ path: SS + "21-empty.png", fullPage: true });
  // error
  await page.unroute(L);
  await page.route(L, (r) => r.fulfill({ status: 500, json: { error: { code: "X", message: "boom" } } }));
  await page.goto("/settlement");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("button", { name: /retry/i })).toBeVisible();
  await page.screenshot({ path: SS + "22-error.png", fullPage: true });
  // files + names + repeated run
  const files = [
    { id: "stl_a", business_date: "2026-10-04", kind: "primary", row_count: 3, checksum: "abc123", written_at: "2026-10-04T10:00:00Z" },
    { id: "stl_b", business_date: "2026-10-04", kind: "followup", row_count: 1, checksum: "def456", written_at: "2026-10-04T12:00:00Z" },
  ];
  await page.unroute(L);
  await page.route(L, (r) => r.fulfill({ json: { items: files, total: 2 } }));
  await page.route(`${API}/settlement/run`, (r) => r.fulfill({ json: { file: files[1], message: REPEAT } }));
  await page.goto("/settlement");
  await expect(page.locator("table.data tbody tr")).toHaveCount(2);
  await expect(page.getByRole("link", { name: "Download CSV: primary settlement file for 2026-10-04" })).toHaveAttribute("href", "/settlement/files/stl_a");
  await expect(page.getByRole("link", { name: "Download CSV: followup settlement file for 2026-10-04" })).toBeVisible();
  await expect(page.getByRole("columnheader")).toHaveText(["Business date", "Kind", "Rows", "Checksum (sha256)", "Download"]);
  const postP = page.waitForRequest((r) => r.url() === `${API}/settlement/run` && r.method() === "POST");
  await page.getByRole("button", { name: "Run now" }).click();
  await postP;
  await expect(page.getByRole("status")).toHaveText(REPEAT);
  await page.screenshot({ path: SS + "23-repeat.png", fullPage: true });
});

for (const [role, cid, labels] of [
  ["ops", null, ["Reconciliation", "Stuck payments"]],
  ["customer", "cus_001", ["Payments"]],
] as const) {
  test(`E7-S3 nav hides Settlement for ${role}`, async ({ page }) => {
    await page.addInitScript((s) => window.localStorage.setItem("paybridge.session", JSON.stringify(s)), session(role, cid));
    await page.goto("/");
    await expect(page.getByRole("navigation").getByRole("link")).toHaveText([...labels]);
    await expect(page.getByRole("link", { name: "Settlement" })).toHaveCount(0);
    await page.screenshot({ path: SS + `30-nav-${role}.png`, fullPage: true });
  });
}
