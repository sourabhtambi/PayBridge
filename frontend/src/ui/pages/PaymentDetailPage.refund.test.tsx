import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PaymentDetailPage } from "./PaymentDetailPage";

const detail = (state: string, refund: unknown = null) => ({
  id: "p1", customer_id: "c", amount_paise: 250000, rail: "UPI", beneficiary: "A", state, reason_code: null,
  refund, created_at: "2026-10-04T09:30:00Z", events: [], attempts: [],
});
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
afterEach(() => { vi.restoreAllMocks(); window.localStorage.clear(); });

function mock(d: unknown, postStatus = 201) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((_u, init) =>
    Promise.resolve(init?.method === "POST" ? json({}, postStatus) : json(d)));
}

test("button only on COMPLETED without refund", async () => {
  mock(detail("SUBMITTED"));
  const { unmount } = render(<PaymentDetailPage id="p1" />);
  await screen.findByText("Rs 2,500.00");
  expect(screen.queryByRole("button", { name: "Request refund" })).toBeNull();
  unmount();
  vi.restoreAllMocks();
  mock(detail("COMPLETED", { id: "r", state: "REQUESTED", reason_code: null }));
  render(<PaymentDetailPage id="p1" />);
  await screen.findByText("Refund requested");
  expect(screen.queryByRole("button", { name: "Request refund" })).toBeNull();
});

test("click disables then shows Refund requested", async () => {
  const f = mock(detail("COMPLETED"));
  render(<PaymentDetailPage id="p1" />);
  await userEvent.click(await screen.findByRole("button", { name: "Request refund" }));
  expect(await screen.findByText("Refund requested")).toBeInTheDocument();
  expect(f.mock.calls.some(([u, i]) => String(u).endsWith("/refunds") && i?.method === "POST")).toBe(true);
  expect(screen.queryByRole("button", { name: "Request refund" })).toBeNull();
});

test("409 shows message, generic error on 500", async () => {
  mock(detail("COMPLETED"), 409);
  render(<PaymentDetailPage id="p1" />);
  await userEvent.click(await screen.findByRole("button", { name: "Request refund" }));
  expect(await screen.findByText("A refund was already requested for this payment")).toBeInTheDocument();
  vi.restoreAllMocks();
  mock(detail("COMPLETED"), 500);
  await userEvent.click(screen.getByRole("button", { name: "Request refund" }));
  expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
});

test("rejected and failed show reason code", async () => {
  mock(detail("COMPLETED", { id: "r", state: "REJECTED", reason_code: "POLICY_VIOLATION" }));
  render(<PaymentDetailPage id="p1" />);
  await waitFor(() => expect(screen.getByText("REJECTED")).toBeInTheDocument());
  expect(screen.getByText("POLICY_VIOLATION")).toBeInTheDocument();
});
