import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { NewPaymentPage } from "./NewPaymentPage";

const respond = (status: number, body: unknown = { id: "pay_1" }) =>
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(body), { status }));

async function fill(amount: string, ben = "Acme") {
  const u = userEvent.setup();
  await u.type(screen.getByLabelText("Amount (Rs)"), amount);
  if (ben) await u.type(screen.getByLabelText("Beneficiary"), ben);
  return u;
}
beforeEach(() => { vi.restoreAllMocks(); window.history.pushState({}, "", "/payments/new"); });

test("preview and labels", async () => {
  render(<NewPaymentPage />);
  expect(screen.getByTestId("rail-preview")).toHaveAttribute("data-rail", "none");
  await fill("200000.01");
  expect(screen.getByTestId("rail-preview")).toHaveAttribute("data-rail", "NEFT");
  expect((screen.getByLabelText("Idempotency key") as HTMLInputElement).value).toMatch(/^[0-9a-f-]{36}$/);
});

test("client validation for zero and empty beneficiary", async () => {
  const f = respond(202);
  render(<NewPaymentPage />);
  const u = await fill("0", "");
  expect(screen.getByText("Amount must be at least Rs 1")).toBeInTheDocument();
  await u.click(screen.getByRole("button", { name: "Pay" }));
  expect(screen.getByText("Enter a beneficiary")).toBeInTheDocument();
  expect(f).not.toHaveBeenCalled();
});

test("202 sends paise, navigates, regenerates key", async () => {
  const f = respond(202);
  render(<NewPaymentPage />);
  const before = (screen.getByLabelText("Idempotency key") as HTMLInputElement).value;
  const u = await fill("1,00,000.50");
  await u.click(screen.getByRole("button", { name: "Pay" }));
  await waitFor(() => expect(window.location.pathname).toBe("/payments/pay_1"));
  const init = f.mock.calls[0][1] as RequestInit;
  expect(JSON.parse(init.body as string)).toEqual({ amount_paise: 10000050, beneficiary: "Acme" });
  expect((init.headers as Record<string, string>)["Idempotency-Key"]).toBe(before);
  expect((screen.getByLabelText("Idempotency key") as HTMLInputElement).value).not.toBe(before);
});

test("200 replay message and navigation", async () => {
  const customers = { items: [{ id: "cus_001", name: "Asha", role: "customer" }], total: 1 };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    String(url).includes("/customers")
      ? new Response(JSON.stringify(customers), { status: 200 })
      : new Response(JSON.stringify({ id: "pay_1", customer_id: "cus_001", amount_paise: 500, rail: "UPI", beneficiary: "A", state: "COMPLETED", reason_code: null, created_at: "2026-10-04T09:30:00Z", events: [], attempts: [] }), { status: 200 }));
  render(<App />);
  const u = await fill("5");
  await u.click(screen.getByRole("button", { name: "Pay" }));
  expect(await screen.findByText("This payment was already created. Showing the original.")).toBeInTheDocument();
  expect(window.location.pathname).toBe("/payments/pay_1");
  expect(screen.queryByRole("form", { name: "New payment" })).not.toBeInTheDocument();
});

test("invalid response id is a generic error, no navigation", async () => {
  respond(202, { id: "../x?y" });
  render(<NewPaymentPage />);
  const u = await fill("5");
  await u.click(screen.getByRole("button", { name: "Pay" }));
  expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
  expect(window.location.pathname).toBe("/payments/new");
});

test("409, 422 and other errors", async () => {
  respond(409, {});
  render(<NewPaymentPage />);
  const u = await fill("5");
  await u.click(screen.getByRole("button", { name: "Pay" }));
  expect(await screen.findByText(/already submitted with different details/)).toBeInTheDocument();
  respond(422, {});
  await u.click(screen.getByRole("button", { name: "Pay" }));
  expect(await screen.findByText("Amount must be at least Rs 1")).toBeInTheDocument();
  respond(500, {});
  await u.click(screen.getByRole("button", { name: "Pay" }));
  expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("net"));
  await u.click(screen.getByRole("button", { name: "Pay" }));
  expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
});

test("disabled with progress label while pending", async () => {
  let release: (r: Response) => void = () => {};
  vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise((r) => { release = r; }));
  render(<NewPaymentPage />);
  const u = await fill("5");
  await u.click(screen.getByRole("button", { name: "Pay" }));
  expect(screen.getByRole("button", { name: "Submitting…" })).toBeDisabled();
  release(new Response("{}", { status: 500 }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Pay" })).toBeEnabled());
});
