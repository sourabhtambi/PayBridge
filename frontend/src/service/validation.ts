import { parseRupeesToPaise } from "./money";
import { MIN_PAISE } from "../config/rails";
import { AMOUNT_MIN_MESSAGE } from "./errorMessages";

export function validateAmount(amount: string): string | null {
  const paise = parseRupeesToPaise(amount);
  return paise === null || paise < MIN_PAISE ? AMOUNT_MIN_MESSAGE : null;
}

export function validateBeneficiary(value: string): string | null {
  return value.trim() ? null : "Enter a beneficiary";
}
