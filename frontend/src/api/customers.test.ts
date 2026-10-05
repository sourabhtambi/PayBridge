import { afterEach, expect, it, vi } from "vitest";
import { fetchCustomers } from "./customers";

afterEach(() => vi.unstubAllGlobals());

it("returns only customer-role users", async () => {
  const items = [
    { id: "adm_001", name: "Admin", role: "admin" },
    { id: "cus_001", name: "Asha Verma", role: "customer" },
    { id: "ops_001", name: "Ops Analyst", role: "ops" },
    { id: "cus_002", name: "Rohan Mehta", role: "customer" },
  ];
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ items, total: 4 }))));
  expect((await fetchCustomers()).map((c) => c.id)).toEqual(["cus_001", "cus_002"]);
});
