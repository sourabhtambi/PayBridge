import { parseRupeesToPaise } from "./money";

import { IMPS_MAX_PAISE, MIN_PAISE, NEFT_MAX_PAISE, UPI_MAX_PAISE } from "../config/rails";
import type { Rail } from "../config/rails";

export type { Rail };

export function railForPaise(paise: number): Rail | null {
  if (paise < MIN_PAISE) return null;
  if (paise <= UPI_MAX_PAISE) return "UPI";
  if (paise <= IMPS_MAX_PAISE) return "IMPS";
  if (paise <= NEFT_MAX_PAISE) return "NEFT";
  return "RTGS";
}

export function previewRail(amount: string): Rail | null {
  const paise = parseRupeesToPaise(amount);
  return paise === null ? null : railForPaise(paise);
}
