import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionProvider } from "../state/SessionContext";
import { RoleSwitcher } from "./RoleSwitcher";
import { NavBar } from "./NavBar";
import { useSession } from "../state/SessionContext";

const customers = { items: [{ id: "cus_001", name: "Asha", role: "customer" }, { id: "cus_002", name: "Ravi", role: "customer" }], total: 2 };

function mount() {
  return render(<SessionProvider><RoleSwitcher /><NavBar /></SessionProvider>);
}

beforeEach(() => {
  window.localStorage.clear();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => customers }));
});
afterEach(() => vi.unstubAllGlobals());

describe("RoleSwitcher", () => {
  it("has a Role select with three options", () => {
    mount();
    const sel = screen.getByLabelText("Role");
    expect(Array.from((sel as HTMLSelectElement).options).map((o) => o.text)).toEqual(["Customer", "Ops", "Admin"]);
  });
  it("shows picker only for customer, populated from /customers", async () => {
    const user = userEvent.setup();
    mount();
    expect(await screen.findByRole("option", { name: "Ravi (cus_002)" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Role"), "ops");
    expect(screen.queryByLabelText("Customer")).toBeNull();
  });
  it("persists selection and sends headers", async () => {
    const user = userEvent.setup();
    mount();
    await screen.findByRole("option", { name: "Ravi (cus_002)" });
    await user.selectOptions(screen.getByLabelText("Customer"), "cus_002");
    expect(JSON.parse(window.localStorage.getItem("paybridge.session") as string)).toEqual({ role: "customer", customerId: "cus_002" });
  });
  it("shows loading state while fetching", async () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => undefined)));
    mount();
    expect(await screen.findByRole("option", { name: "Loading customers…" })).toBeInTheDocument();
    expect(screen.getByLabelText("Customer")).toBeDisabled();
  });
  it("shows error with Retry that refetches", async () => {
    const user = userEvent.setup();
    const f = vi.fn().mockRejectedValueOnce(new Error("down")).mockResolvedValue({ ok: true, json: async () => customers });
    vi.stubGlobal("fetch", f);
    mount();
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load customers");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("option", { name: "Ravi (cus_002)" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });
  it("throws outside provider", () => {
    const Bad = () => { useSession(); return null; };
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<Bad />)).toThrow();
  });
});
