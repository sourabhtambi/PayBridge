import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PaymentsListPage } from "./PaymentsListPage";
import { formatRupees } from "../../service/format";

const pay = (id: string, state: string, extra = {}) => ({
  id, customer_id: "cus_001", amount_paise: 10000050, rail: "IMPS", beneficiary: "A",
  state, reason_code: null, created_at: "2026-10-04T09:30:00Z", ...extra,
});
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
beforeEach(() => vi.restoreAllMocks());

test("formatRupees", () => {
  expect(formatRupees(10000050)).toBe("Rs 1,00,000.50");
  expect(formatRupees(5)).toBe("Rs 0.05");
  expect(formatRupees(-123456)).toBe("-Rs 1,234.56");
});

test("rows, badges, reason code, links, caption", async () => {
  const items = [pay("p1", "CREATED"), pay("p2", "SUBMITTED"), pay("p3", "COMPLETED"), pay("p4", "FAILED", { reason_code: "INSUFFICIENT_FUNDS" })];
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items, total: 4 }));
  render(<PaymentsListPage />);
  expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThan(0);
  expect(await screen.findByText("p1")).toHaveAttribute("href", "/payments/p1");
  expect(screen.getByRole("table", { name: "My payments" })).toBeInTheDocument();
  for (const s of ["CREATED", "SUBMITTED", "COMPLETED", "FAILED"]) expect(screen.getByText(s)).toBeInTheDocument();
  expect(screen.getAllByText("Rs 1,00,000.50")).toHaveLength(4);
  expect(screen.getAllByText("INSUFFICIENT_FUNDS")).toHaveLength(1);
  expect(within(screen.getByText("p3").closest("tr")!).getByText("—")).toBeInTheDocument();
});

test("empty state", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [], total: 0 }));
  render(<PaymentsListPage />);
  expect(await screen.findByText("No payments yet")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Create your first payment" })).toHaveAttribute("href", "/payments/new");
});

test("error banner retries", async () => {
  const f = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json({}, 500))
    .mockResolvedValueOnce(json({ items: [pay("p1", "COMPLETED")], total: 1 }));
  render(<PaymentsListPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Request failed: 500");
  await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(screen.getByText("p1")).toBeInTheDocument());
  expect(f).toHaveBeenCalledTimes(2);
  expect(screen.queryByRole("alert")).toBeNull();
});
