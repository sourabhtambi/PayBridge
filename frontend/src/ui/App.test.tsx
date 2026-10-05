import { StrictMode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { setFlash } from "../service/flash";

afterEach(() => {
  window.history.pushState({}, "", "/");
  vi.unstubAllGlobals();
});

it("shows the flash notice on payment detail under StrictMode", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 404 })));
  window.history.pushState({}, "", "/payments/pay_1");
  setFlash("Already created.");
  render(<StrictMode><App /></StrictMode>);
  expect(await screen.findByRole("status")).toHaveTextContent("Already created.");
});

it("navigates to the role's default page when the role changes, not on first load", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 404 })));
  window.sessionStorage.clear();
  window.history.pushState({}, "", "/payments/pay_1");
  render(<App />);
  expect(window.location.pathname).toBe("/payments/pay_1");
  const select = screen.getByLabelText("Role");
  await userEvent.selectOptions(select, "ops");
  expect(window.location.pathname).toBe("/reconciliation");
  await userEvent.selectOptions(select, "admin");
  expect(window.location.pathname).toBe("/dashboard");
  await userEvent.selectOptions(select, "customer");
  expect(window.location.pathname).toBe("/payments");
});

it("leaves a payment detail for the list when the customer changes", async () => {
  const customers = { items: [
    { id: "cus_001", name: "A", role: "customer" },
    { id: "cus_002", name: "B", role: "customer" },
  ], total: 2 };
  vi.stubGlobal("fetch", vi.fn((url: string) =>
    Promise.resolve(url.endsWith("/customers")
      ? new Response(JSON.stringify(customers), { status: 200 })
      : new Response("{}", { status: 404 })),
  ));
  window.localStorage.setItem("paybridge.session", JSON.stringify({ role: "customer", customerId: "cus_001" }));
  window.history.pushState({}, "", "/payments/pay_1");
  render(<App />);
  await waitFor(() => expect(screen.getByLabelText("Customer")).toBeEnabled());
  expect(window.location.pathname).toBe("/payments/pay_1");
  await userEvent.selectOptions(screen.getByLabelText("Customer"), "cus_002");
  expect(window.location.pathname).toBe("/payments");
  window.localStorage.clear();
});
