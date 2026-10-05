/** Parse a rupee string (e.g. "1,00,000.50") into integer paise without floating point. */
export function parseRupeesToPaise(input: string): number | null {
  const cleaned = input.trim().replace(/,/g, "");
  const m = /^(\d+)(?:\.(\d{1,2}))?$/.exec(cleaned);
  if (!m) return null;
  const paise = Number(m[1] + (m[2] ?? "").padEnd(2, "0"));
  return Number.isSafeInteger(paise) ? paise : null;
}
