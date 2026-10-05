import { act, render, screen } from "@testing-library/react";
import { PaymentDetailPage } from "./PaymentDetailPage";

const detail = (state: string, extra = {}) => ({
  id: "p1", customer_id: "c", amount_paise: 250000, rail: "UPI", beneficiary: "A", state, reason_code: null,
  created_at: "2026-10-04T09:30:00Z",
  events: [
    { id: "e2", type: "PAYMENT_SUBMITTED", payload: {}, at: "2026-10-04T09:30:02Z" },
    { id: "e1", type: "PAYMENT_CREATED", payload: {}, at: "2026-10-04T09:30:00Z" },
  ],
  attempts: [{ attempt_no: 1, outcome: "SUCCESS", error_code: null, at: "2026-10-04T09:30:02Z" }],
  ...extra,
});
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

test("fields, ordered timeline, attempts, skeleton", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json(detail("COMPLETED")));
  render(<PaymentDetailPage id="p1" />);
  expect(screen.getByTestId("skeleton-timeline")).toBeInTheDocument();
  expect(await screen.findByText("Rs 2,500.00")).toBeInTheDocument();
  const items = screen.getAllByRole("listitem").map((li) => li.textContent ?? "");
  expect(items[0]).toContain("PAYMENT_CREATED");
  expect(items[1]).toContain("PAYMENT_SUBMITTED");
  expect(screen.getByRole("table", { name: "Attempts" })).toHaveTextContent("SUCCESS");
});

test("polls every 2s until terminal", async () => {
  vi.useFakeTimers();
  const f = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json(detail("CREATED")))
    .mockResolvedValueOnce(json(detail("SUBMITTED")))
    .mockResolvedValue(json(detail("COMPLETED")));
  render(<PaymentDetailPage id="p1" />);
  await act(() => vi.advanceTimersByTimeAsync(0));
  expect(f).toHaveBeenCalledTimes(1);
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(f).toHaveBeenCalledTimes(2);
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(f).toHaveBeenCalledTimes(3);
  await act(() => vi.advanceTimersByTimeAsync(10000));
  expect(f).toHaveBeenCalledTimes(3);
});

test("failed shows reason code", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json(detail("FAILED", { reason_code: "INSUFFICIENT_FUNDS" })));
  render(<PaymentDetailPage id="p1" />);
  expect(await screen.findByRole("note")).toHaveTextContent("INSUFFICIENT_FUNDS");
});

test("404 shows not found with back link", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({}, 404));
  render(<PaymentDetailPage id="nope" />);
  expect(await screen.findByText("Payment not found")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Back to payments" })).toHaveAttribute("href", "/payments");
});

test("other error offers retry", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({}, 500));
  render(<PaymentDetailPage id="p1" />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Request failed: 500");
});
