import { StrictMode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { App } from "./App";
import { setFlash } from "../service/flash";

afterEach(() => {
  window.history.pushState({}, "", "/");
  vi.unstubAllGlobals();
});

it("shows the flash notice on payment detail under StrictMode", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 404 })));
  window.history.pushState({}, "", "/payments/pay_1");
  setFlash("Already created.");
  render(<StrictMode><App /></StrictMode>);
  expect(await screen.findByRole("status")).toHaveTextContent("Already created.");
});
