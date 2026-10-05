const KEY = "paybridge.flash";

export function setFlash(text: string): void {
  try { sessionStorage.setItem(KEY, text); } catch { /* storage unavailable */ }
}

export function takeFlash(): string | null {
  try {
    const v = sessionStorage.getItem(KEY);
    sessionStorage.removeItem(KEY);
    return v;
  } catch { return null; }
}
