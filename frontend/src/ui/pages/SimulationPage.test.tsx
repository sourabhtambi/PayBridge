import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SimulationPage } from "./SimulationPage";

const items = ["UPI", "IMPS", "NEFT", "RTGS"].map((rail) => ({ rail, mode: "success", reason_code: null, transient_failure_rate: 0 }));
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
beforeEach(() => vi.restoreAllMocks());

test("one card per rail, labelled controls", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items }));
  render(<SimulationPage />);
  expect(await screen.findAllByRole("form")).toHaveLength(4);
  expect(screen.getAllByLabelText("Reason code (used for permanent failure)")).toHaveLength(4);
  expect(screen.getAllByLabelText("Transient failure rate (0 to 1)")).toHaveLength(4);
  expect(screen.getByRole("group", { name: "UPI mode" })).toBeInTheDocument();
});

test("invalid rate shows error and does not call PUT", async () => {
  const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items }));
  render(<SimulationPage />);
  const u = userEvent.setup();
  const input = (await screen.findAllByLabelText("Transient failure rate (0 to 1)"))[0];
  await u.clear(input);
  await u.type(input, "1.5");
  await u.click(screen.getByRole("button", { name: "Save UPI" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Enter a rate between 0 and 1");
  expect(f).toHaveBeenCalledTimes(1);
});

test("save calls PUT and confirms", async () => {
  const f = vi.spyOn(globalThis, "fetch").mockImplementation(async (_u, init) =>
    init?.method === "PUT" ? json({ ...items[0], mode: "permanent_failure", reason_code: "LIMIT_EXCEEDED" }) : json({ items }));
  render(<SimulationPage />);
  const u = userEvent.setup();
  await screen.findAllByRole("form");
  await u.click(document.getElementById("mode-UPI-permanent_failure")!);
  await u.selectOptions(document.getElementById("reason-UPI")!, "LIMIT_EXCEEDED");
  await u.click(screen.getByRole("button", { name: "Save UPI" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Saved");
  const put = f.mock.calls.find((c) => c[1]?.method === "PUT")!;
  expect(String(put[0])).toContain("/admin/simulation/UPI");
  expect(JSON.parse(put[1]!.body as string)).toEqual({ mode: "permanent_failure", reason_code: "LIMIT_EXCEEDED", transient_failure_rate: 0 });
});

test("save failure and load failure show errors", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (_u, init) =>
    init?.method === "PUT" ? json({}, 500) : json({ items }));
  render(<SimulationPage />);
  await screen.findAllByRole("form");
  await userEvent.setup().click(screen.getByRole("button", { name: "Save UPI" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Request failed: 500");
});

test("load error retries", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({}, 500)).mockResolvedValueOnce(json({ items }));
  render(<SimulationPage />);
  await userEvent.setup().click(await screen.findByRole("button", { name: "Retry" }));
  await waitFor(() => expect(screen.getAllByRole("form")).toHaveLength(4));
});
