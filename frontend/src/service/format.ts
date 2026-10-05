/** Integer paise to "Rs 1,00,000.50" (Indian grouping) using string ops only. */
export function formatRupees(paise: number): string {
  const abs = Math.abs(paise);
  const rupees = String(Math.floor(abs / 100));
  const pa = String(abs % 100).padStart(2, "0");
  const head = rupees.length > 3 ? rupees.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," : "";
  return `${paise < 0 ? "-" : ""}Rs ${head}${rupees.slice(-3)}.${pa}`;
}

export function formatCreated(iso: string): string {
  return (
    new Intl.DateTimeFormat("en-IN", {
      timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit", hour12: false,
    }).format(new Date(iso)) + " IST"
  );
}
