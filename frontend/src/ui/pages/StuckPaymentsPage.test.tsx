import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StuckPaymentsPage, formatAge } from "./StuckPaymentsPage";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
beforeEach(() => vi.restoreAllMocks());

test("formatAge", () => {
  expect(formatAge(420)).toBe("7m");
  expect(formatAge(3900)).toBe("1h 5m");
});

test("lists stuck payments", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [{ payment_id: "pay_1", rail: "NEFT", amount_paise: 250000, age_seconds: 420 }] }));
  render(<StuckPaymentsPage />);
  expect(await screen.findByText("pay_1")).toBeInTheDocument();
  expect(screen.getByText("NEFT")).toBeInTheDocument();
  expect(screen.getByText("Rs 2,500.00")).toBeInTheDocument();
  expect(screen.getByText("7m")).toBeInTheDocument();
});

test("empty", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [] }));
  render(<StuckPaymentsPage />);
  expect(await screen.findByText("No stuck payments")).toBeInTheDocument();
});

test("error banner retries", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({}, 500)).mockResolvedValueOnce(json({ items: [] }));
  render(<StuckPaymentsPage />);
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByText("No stuck payments")).toBeInTheDocument();
});
