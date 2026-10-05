import { parseRupeesToPaise } from "./money";
import { previewRail } from "./railPreview";
import { validateAmount, validateBeneficiary } from "./validation";

test("parses paise by string", () => {
  expect(parseRupeesToPaise("1,00,000.50")).toBe(10000050);
  expect(parseRupeesToPaise("0.5")).toBe(50);
  expect(parseRupeesToPaise("abc")).toBeNull();
  expect(parseRupeesToPaise("99999999999999999999")).toBeNull();
});
test.each([["1,00,000", "UPI"], ["100000.50", "IMPS"], ["200000.01", "NEFT"], ["500000.01", "RTGS"], ["0.99", null], ["x", null]])(
  "rail for %s", (a, r) => expect(previewRail(a)).toBe(r));
test("validation", () => {
  expect(validateAmount("0")).toBe("Amount must be at least Rs 1");
  expect(validateAmount("5")).toBeNull();
  expect(validateBeneficiary(" ")).not.toBeNull();
  expect(validateBeneficiary("A")).toBeNull();
});
