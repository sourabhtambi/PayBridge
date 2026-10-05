import { render, screen } from "@testing-library/react";
import { Dialog } from "./Dialog";

test("renders titled dialog", () => {
  render(<Dialog title="Hello" onClose={() => {}}><button>ok</button></Dialog>);
  expect(screen.getByRole("dialog", { name: "Hello" })).toBeInTheDocument();
});
