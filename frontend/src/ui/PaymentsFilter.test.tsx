import { afterEach, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { listPayments } from "../api/payments";

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

afterEach(() => {
  window.localStorage.clear();
  window.history.pushState({}, "", "/");
  vi.unstubAllGlobals();
});

it("listPayments sends customer_id as a query parameter for a customer session", async () => {
  const fetchMock = vi.fn().mockResolvedValue(json({ items: [], total: 0 }));
  vi.stubGlobal("fetch", fetchMock);
  window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "customer", customerId: "cus_002" }));
  await listPayments();
  expect(String(fetchMock.mock.calls[0][0])).toContain("/payments?customer_id=cus_002");
});

it("listPayments sends no customer_id for ops/admin", async () => {
  const fetchMock = vi.fn().mockResolvedValue(json({ items: [], total: 0 }));
  vi.stubGlobal("fetch", fetchMock);
  window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "ops", customerId: "cus_002" }));
  await listPayments();
  expect(String(fetchMock.mock.calls[0][0])).not.toContain("customer_id");
});

it("reloads the payments list when the customer changes", async () => {
  const fetchMock = vi.fn((url: string) => {
    if (url.endsWith("/customers")) {
      return Promise.resolve(json({ items: [
        { id: "cus_001", name: "A", role: "customer" },
        { id: "cus_002", name: "B", role: "customer" },
      ], total: 2 }));
    }
    return Promise.resolve(json({ items: [], total: 0 }));
  });
  vi.stubGlobal("fetch", fetchMock);
  window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "customer", customerId: "cus_001" }));
  window.history.pushState({}, "", "/payments");
  render(<App />);
  await waitFor(() => expect(screen.getByLabelText("Customer")).toBeEnabled());
  await userEvent.selectOptions(screen.getByLabelText("Customer"), "cus_002");
  await waitFor(() =>
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes("/payments?customer_id=cus_002"))).toBe(true),
  );
});
