import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";

beforeEach(() => {
  window.localStorage.clear();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [], total: 0 }) }));
});

const links = () => screen.getAllByRole("link").map((l) => l.textContent).filter((t) => t !== "Skip to main content");

describe("NavBar", () => {
  it("shows role-specific items only", async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(links()).toEqual(["Payments"]);
    await user.selectOptions(screen.getByLabelText("Role"), "ops");
    expect(links()).toEqual(["Reconciliation", "Stuck payments"]);
    await user.selectOptions(screen.getByLabelText("Role"), "admin");
    expect(links()).toEqual(["Dashboard", "Settlement", "Simulation"]);
  });
  it("marks current page", () => {
    window.history.pushState({}, "", "/payments");
    render(<App />);
    expect(screen.getByRole("link", { name: "Payments" })).toHaveAttribute("aria-current", "page");
  });
  it("updates current page on navigation", () => {
    window.history.pushState({}, "", "/other");
    render(<App />);
    expect(screen.getByRole("link", { name: "Payments" })).not.toHaveAttribute("aria-current");
    act(() => {
      window.history.pushState({}, "", "/payments");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(screen.getByRole("link", { name: "Payments" })).toHaveAttribute("aria-current", "page");
  });
});
