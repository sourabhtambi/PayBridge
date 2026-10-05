import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StateBadge } from "./StateBadge";

describe("StateBadge", () => {
  it("renders REFUNDED with its own tone, glyph and data-state", () => {
    render(<StateBadge state="REFUNDED" />);
    const badge = screen.getByText("REFUNDED").closest(".badge");
    expect(badge).toHaveAttribute("data-state", "REFUNDED");
    expect(badge).toHaveClass("warn");
    expect(badge?.textContent).toContain("↩");
  });
});
