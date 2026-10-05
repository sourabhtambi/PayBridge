import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DashboardPage, todayIST } from "./DashboardPage";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const refund = { id: "ref_1", payment_id: "pay_1", amount_paise: 250000, state: "REQUESTED", requested_by: "cus_001" };
const file = { id: "stl_1", business_date: "2026-10-04", kind: "primary", row_count: 58, checksum: "x", written_at: "2026-10-04T18:00:00Z" };
const rails = (n: number) => ["UPI", "IMPS", "NEFT", "RTGS"].map((rail) => ({ rail, payment_count: n, total_paise: n * 10000050 }));
const summary = (n: number, refunds: unknown[] = [], files: unknown[] = []) => ({
  date: "2026-10-04", rails: rails(n), status_counts: { CREATED: n, SUBMITTED: 0, COMPLETED: 2, FAILED: 1, REFUNDED: 0 },
  pending_refunds: refunds, settlement_files: files,
});
beforeEach(() => { vi.restoreAllMocks(); window.localStorage.clear(); });

test("shows rail tiles with Indian grouping and status labels", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => json(summary(1, [], [file])));
  render(<DashboardPage />);
  const upi = await screen.findByText("UPI");
  expect(within(upi.closest("[data-rail]") as HTMLElement).getByText("Rs 1,00,000.50")).toBeInTheDocument();
  expect(await screen.findByText("COMPLETED")).toBeInTheDocument();
  expect(screen.getByText("FAILED")).toBeInTheDocument();
  expect(await screen.findByText("58")).toBeInTheDocument();
  expect(screen.queryByText("No activity for this date")).not.toBeInTheDocument();
});

test("no activity shows zeros and message", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => json(summary(0)));
  render(<DashboardPage />);
  expect(await screen.findByText("No activity for this date")).toBeInTheDocument();
  expect((await screen.findAllByText("Rs 0.00")).length).toBe(4);
  expect(await screen.findByText("No refunds pending")).toBeInTheDocument();
  expect(await screen.findByText("No settlement files for this date")).toBeInTheDocument();
});

test("date picker defaults to today IST and refetches on change", async () => {
  const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async () => json(summary(0)));
  render(<DashboardPage />);
  const input = screen.getByLabelText("Date (IST)") as HTMLInputElement;
  expect(input.value).toBe(todayIST());
  await screen.findByText("No activity for this date");
  const calls = spy.mock.calls.length;
  fireEvent.change(input, { target: { value: "2026-01-02" } });
  expect(input.value).toBe("2026-01-02");
  await waitFor(() => expect(spy.mock.calls.length).toBeGreaterThan(calls));
  expect(String(spy.mock.calls.at(-1)?.[0])).toContain("date=2026-01-02");
});

test("approve updates the row and pending count; links to /refunds", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    String(url).includes("/approve") ? json({ ...refund, state: "EXECUTED" }) : json(summary(1, [refund])));
  render(<DashboardPage />);
  expect(await screen.findByText("1 pending")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open full refund queue" })).toHaveAttribute("href", "/refunds");
  await userEvent.setup().click(await screen.findByRole("button", { name: "Approve refund for payment pay_1" }));
  expect(await screen.findByText("EXECUTED")).toBeInTheDocument();
  expect(screen.getByText("0 pending")).toBeInTheDocument();
});

test("reject conflict and generic failure show notices", async () => {
  let status = 409;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    String(url).includes("/reject") ? json({}, status) : json(summary(1, [refund])));
  render(<DashboardPage />);
  const btn = await screen.findByRole("button", { name: "Reject refund for payment pay_1" });
  await userEvent.setup().click(btn);
  expect(await screen.findByText("This refund was already decided")).toBeInTheDocument();
  status = 500;
  await userEvent.setup().click(btn);
  expect(await screen.findByText("Something went wrong. Please try again.")).toBeInTheDocument();
});

test("tile error shows retry for that tile only", async () => {
  let broken = true;
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
    const s = summary(1) as Record<string, unknown>;
    if (broken) delete s.status_counts;
    return json(s);
  });
  render(<DashboardPage />);
  const retry = await screen.findByRole("button", { name: "Retry" });
  expect(screen.getAllByRole("button", { name: "Retry" })).toHaveLength(1);
  expect(within(retry.closest("[data-tile]") as HTMLElement).getByText("Status breakdown")).toBeInTheDocument();
  broken = false;
  await userEvent.setup().click(retry);
  expect(await screen.findByText("SUBMITTED")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
});
