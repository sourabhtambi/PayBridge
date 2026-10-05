import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReconciliationPage } from "./ReconciliationPage";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const row = { id: "rr_1", rail: "UPI", status: "amount_mismatch", payment_amount_paise: 10000, statement_amount_paise: 9000 };
beforeEach(() => vi.restoreAllMocks());

test("lists unmatched with status, rail, amounts", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [row], total: 1 }));
  render(<ReconciliationPage />);
  expect(await screen.findByText("amount_mismatch")).toBeInTheDocument();
  expect(screen.getByText("UPI")).toBeInTheDocument();
  expect(screen.getByText("Rs 100.00")).toBeInTheDocument();
  expect(screen.getByText("Rs 90.00")).toBeInTheDocument();
});

test("empty, skeleton and error retry", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({}, 500)).mockResolvedValueOnce(json({ items: [], total: 0 }));
  render(<ReconciliationPage />);
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByText("Nothing to reconcile")).toBeInTheDocument();
});

test("shows skeleton while loading", () => {
  vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
  render(<ReconciliationPage />);
  expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThan(0);
});

test("run shows counts, handles failure", async () => {
  const counts = { matched: 5, unmatched_internal: 1, unmatched_external: 2, amount_mismatch: 3 };
  const f = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json({ items: [], total: 0 }))
    .mockResolvedValueOnce(json({ statement_date: "2026-10-04", counts }))
    .mockResolvedValueOnce(json({ items: [], total: 0 }))
    .mockResolvedValueOnce(json({}, 422));
  render(<ReconciliationPage />);
  const u = userEvent.setup();
  await screen.findByText("Nothing to reconcile");
  await u.click(screen.getByRole("button", { name: "Run reconciliation" }));
  expect(await screen.findByText("unmatched_external")).toBeInTheDocument();
  expect(screen.getByText("5")).toBeInTheDocument();
  await waitFor(() => expect(f).toHaveBeenCalledTimes(3));
  await u.click(screen.getByRole("button", { name: "Run reconciliation" }));
  expect(await screen.findByText(/Run failed/)).toBeInTheDocument();
});

test("resolve requires note, removes row, restores focus", async () => {
  const f = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json({ items: [row], total: 1 }))
    .mockResolvedValueOnce(json({}, 500))
    .mockResolvedValueOnce(json({ ...row, resolved: true }));
  render(<ReconciliationPage />);
  const u = userEvent.setup();
  const trigger = await screen.findByRole("button", { name: "Resolve" });
  await u.click(trigger);
  const submit = () => within(screen.getByRole("dialog")).getByRole("button", { name: "Resolve" });
  await u.click(submit());
  expect(await screen.findByText("A note is required")).toBeInTheDocument();
  await u.type(screen.getByLabelText("Resolution note"), "checked");
  await u.click(submit());
  expect(await screen.findByText(/Could not resolve/)).toBeInTheDocument();
  await u.click(submit());
  expect(await screen.findByText("Nothing to reconcile")).toBeInTheDocument();
  expect(f).toHaveBeenCalledTimes(3);
});

test("dialog traps focus and returns it on cancel", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [row], total: 1 }));
  render(<ReconciliationPage />);
  const u = userEvent.setup();
  const trigger = await screen.findByRole("button", { name: "Resolve" });
  trigger.focus();
  await u.click(trigger);
  expect(screen.getByLabelText("Resolution note")).toHaveFocus();
  await u.tab();
  expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
  await u.tab();
  await u.tab();
  expect(screen.getByLabelText("Resolution note")).toHaveFocus();
  await u.tab({ shift: true });
  expect(within(screen.getByRole("dialog")).getByRole("button", { name: "Resolve" })).toHaveFocus();
  await u.tab();
  expect(screen.getByLabelText("Resolution note")).toHaveFocus();
  await u.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(trigger).toHaveFocus();
});
