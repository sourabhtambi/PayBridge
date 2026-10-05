import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest, authHeaders, loadSession, saveSession } from "./client";

beforeEach(() => window.localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe("client", () => {
  it("defaults to customer cus_001", () => {
    expect(loadSession()).toEqual({ role: "customer", customerId: "cus_001" });
  });
  it("persists the session across reload", () => {
    saveSession({ role: "ops", customerId: null });
    expect(loadSession()).toEqual({ role: "ops", customerId: null });
  });
  it("falls back on corrupt storage", () => {
    window.localStorage.setItem("paybridge.session", "{bad");
    expect(loadSession().role).toBe("customer");
    window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "x" }));
    expect(loadSession().role).toBe("customer");
  });
  it("builds headers", () => {
    expect(authHeaders({ role: "customer", customerId: "cus_002" })).toEqual({ "X-Role": "customer", "X-Customer-Id": "cus_002" });
    expect(authHeaders({ role: "admin", customerId: null })).toEqual({ "X-Role": "admin" });
  });
  it("attaches headers to every request", async () => {
    saveSession({ role: "customer", customerId: "cus_003" });
    const f = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ a: 1 }) });
    vi.stubGlobal("fetch", f);
    await apiRequest("/payments");
    expect(f.mock.calls[0][1].headers).toMatchObject({ "X-Role": "customer", "X-Customer-Id": "cus_003" });
  });
  it.each([
    ["customer", "cus_007", { "X-Role": "customer", "X-Customer-Id": "cus_007" }],
    ["ops", null, { "X-Role": "ops" }],
    ["admin", null, { "X-Role": "admin" }],
  ] as const)("apiRequest sends role headers for %s", async (role, customerId, expected) => {
    saveSession({ role, customerId });
    const f = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", f);
    await apiRequest("/payments");
    expect(f.mock.calls[0][1].headers).toEqual(expected);
  });
  it("sends X-Customer-Id for ops/admin only if the session carries one", async () => {
    saveSession({ role: "ops", customerId: "cus_009" });
    const f = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", f);
    await apiRequest("/payments");
    expect(f.mock.calls[0][1].headers).toEqual({ "X-Role": "ops", "X-Customer-Id": "cus_009" });
  });
  it("throws on non-ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    await expect(apiRequest("/x")).rejects.toThrow("401");
  });
  it("ignores storage errors on save", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    expect(() => saveSession({ role: "admin", customerId: null })).not.toThrow();
  });
});
