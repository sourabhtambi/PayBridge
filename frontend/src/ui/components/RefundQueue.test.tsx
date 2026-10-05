import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RefundQueue } from "./RefundQueue";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const refund = { id: "ref_1", payment_id: "pay_1", amount_paise: 10000050, state: "REQUESTED", requested_by: "cus_001" };
beforeEach(() => vi.restoreAllMocks());

test("lists requested refunds with Indian grouping", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [refund] }));
  render(<RefundQueue />);
  expect(await screen.findByText("pay_1")).toBeInTheDocument();
  expect(screen.getByText("Rs 1,00,000.50")).toBeInTheDocument();
  expect(screen.getByText("cus_001")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Approve refund for payment pay_1" })).toBeInTheDocument();
});

test("shows skeleton while loading", () => {
  vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => undefined));
  render(<RefundQueue />);
  expect(screen.getAllByTestId("skeleton-row")).toHaveLength(3);
});

test("empty state", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [] }));
  render(<RefundQueue />);
  expect(await screen.findByText("No refunds pending")).toBeInTheDocument();
});

test("approve updates row to final state", async () => {
  const f = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({ items: [refund] }))
    .mockResolvedValueOnce(json({ ...refund, state: "EXECUTED" }));
  render(<RefundQueue />);
  await userEvent.click(await screen.findByRole("button", { name: /Approve/ }));
  expect(await screen.findByText("EXECUTED")).toBeInTheDocument();
  expect(f.mock.calls[1][0]).toContain("/refunds/ref_1/approve");
  expect(screen.queryByRole("button", { name: /Reject/ })).toBeNull();
});

test("reject updates row", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({ items: [refund] }))
    .mockResolvedValueOnce(json({ ...refund, state: "REJECTED" }));
  render(<RefundQueue />);
  await userEvent.click(await screen.findByRole("button", { name: /Reject/ }));
  expect(await screen.findByText("REJECTED")).toBeInTheDocument();
});

test("409 shows already decided", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({ items: [refund] })).mockResolvedValueOnce(json({}, 409));
  render(<RefundQueue />);
  await userEvent.click(await screen.findByRole("button", { name: /Approve/ }));
  expect(await screen.findByText("This refund was already decided")).toBeInTheDocument();
});

test("other decision error shows generic message", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({ items: [refund] })).mockResolvedValueOnce(json({}, 500));
  render(<RefundQueue />);
  await userEvent.click(await screen.findByRole("button", { name: /Approve/ }));
  expect(await screen.findByText("Something went wrong. Please try again.")).toBeInTheDocument();
});

test("load error banner retries", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({}, 500)).mockResolvedValueOnce(json({ items: [refund] }));
  render(<RefundQueue />);
  await userEvent.click(await screen.findByRole("button", { name: "Retry" }));
  expect(await screen.findByText("pay_1")).toBeInTheDocument();
});
