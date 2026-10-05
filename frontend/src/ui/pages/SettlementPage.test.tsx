import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SettlementPage } from "./SettlementPage";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const file = { id: "stl_1", business_date: "2026-10-03", kind: "primary", row_count: 58, checksum: "abc123", written_at: "2026-10-03T18:29:00Z" };
beforeEach(() => vi.restoreAllMocks());

test("lists files with accessible download link", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [file], total: 1 }));
  render(<SettlementPage />);
  expect(await screen.findByText("2026-10-03")).toBeInTheDocument();
  expect(screen.getByText("primary")).toBeInTheDocument();
  expect(screen.getByText("58")).toBeInTheDocument();
  expect(screen.getByText("abc123")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Download CSV: primary settlement file for 2026-10-03" })).toBeInTheDocument();
});

test("empty", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [], total: 0 }));
  render(<SettlementPage />);
  expect(await screen.findByText("No settlement files yet")).toBeInTheDocument();
});

test("loading shows skeleton rows", () => {
  vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
  render(<SettlementPage />);
  expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThan(0);
});

test("error banner retries", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({}, 500)).mockResolvedValueOnce(json({ items: [], total: 0 }));
  render(<SettlementPage />);
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByText("No settlement files yet")).toBeInTheDocument();
});

test("run now posts and shows repeat message", async () => {
  const msg = "Primary file for this date already exists. Late entries were written to a follow-up file.";
  const spy = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json({ items: [], total: 0 }))
    .mockResolvedValueOnce(json({ file, message: msg }))
    .mockResolvedValueOnce(json({ items: [file], total: 1 }));
  render(<SettlementPage />);
  await screen.findByText("No settlement files yet");
  await userEvent.setup().click(screen.getByRole("button", { name: "Run now" }));
  expect(await screen.findByText(msg)).toBeInTheDocument();
  expect(await screen.findByText("2026-10-03")).toBeInTheDocument();
  expect(spy.mock.calls[1][0]).toContain("/settlement/run");
  expect((spy.mock.calls[1][1] as RequestInit).method).toBe("POST");
});

test("run failure shows error", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({ items: [], total: 0 })).mockResolvedValueOnce(json({}, 500));
  render(<SettlementPage />);
  await screen.findByText("No settlement files yet");
  await userEvent.setup().click(screen.getByRole("button", { name: "Run now" }));
  expect(await screen.findByText("Request failed: 500")).toBeInTheDocument();
});

test("download fetches csv with auth", async () => {
  const spy = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json({ items: [file], total: 1 }))
    .mockResolvedValueOnce(new Response("a,b", { status: 200 }));
  URL.createObjectURL = vi.fn(() => "blob:x");
  URL.revokeObjectURL = vi.fn();
  render(<SettlementPage />);
  await userEvent.setup().click(await screen.findByRole("link", { name: /Download CSV/ }));
  await vi.waitFor(() => expect(URL.revokeObjectURL).toHaveBeenCalled());
  expect(spy.mock.calls[1][0]).toContain("/settlement/files/stl_1");
});

test("download failure shows error", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({ items: [file], total: 1 })).mockResolvedValueOnce(json({}, 404));
  render(<SettlementPage />);
  await userEvent.setup().click(await screen.findByRole("link", { name: /Download CSV/ }));
  expect(await screen.findByText("Request failed: 404")).toBeInTheDocument();
});
