/// <reference types="node" />
import { readFileSync } from "node:fs";

const css = readFileSync("src/ui/styles/tokens.css", "utf8");

const tokens = Object.fromEntries([...css.matchAll(/--([\w-]+):\s*(#[0-9A-Fa-f]{6})/g)].map((m) => [m[1], m[2]]));

function lum(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
export function ratio(fg: string, bg: string): number {
  const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
  return (a + 0.05) / (b + 0.05);
}
const hex = (n: string): string => tokens[`color-${n}`] ?? n;

// Every foreground/background pair used by tokens.css/app.css (text and interactive tokens).
const PAIRS: [string, string][] = [
  ["text", "bg"], ["text", "surface"], ["text-secondary", "surface"], ["text-secondary", "surface-sunken"],
  ["text-muted", "bg"], ["text-muted", "surface"], ["text-muted", "surface-sunken"], ["placeholder", "surface"],
  ["link", "bg"], ["link", "surface"], ["primary-hover", "surface"], ["primary-hover", "surface-sunken"],
  ["on-primary", "primary"], ["on-primary", "primary-hover"], ["primary", "surface"], ["primary", "surface-sunken"],
  ["on-primary", "danger-solid"], ["on-primary", "danger-text"],
  ["nav-text", "nav-bg"], ["nav-text-muted", "nav-bg"], ["nav-text", "nav-active-bg"],
  ["neutral-text", "neutral-bg"], ["info-text", "info-bg"], ["success-text", "success-bg"],
  ["warn-text", "warn-bg"], ["danger-text", "danger-bg"], ["success-text", "surface"], ["info-text", "surface"],
  ["danger-text", "surface"], ["warn-text", "surface"], ["disabled-text", "disabled-bg"],
  ["dev-text", "dev-bg"], ["#b00020", "surface"], ["#b00020", "danger-bg"], ["#1b5e20", "surface"],
];

test.each(PAIRS)("contrast %s on %s >= 4.5:1", (fg, bg) => {
  expect(ratio(hex(fg), hex(bg))).toBeGreaterThanOrEqual(4.5);
});

test("focus ring and field border meet 3:1 non-text contrast", () => {
  expect(ratio(hex("focus-ring"), hex("surface"))).toBeGreaterThanOrEqual(3);
  expect(ratio(hex("focus-ring-on-dark"), hex("nav-bg"))).toBeGreaterThanOrEqual(3);
  expect(ratio(hex("border-strong"), hex("surface"))).toBeGreaterThanOrEqual(3);
});
