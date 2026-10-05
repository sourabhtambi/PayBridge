import { apiRequest } from "./client";
import type { Refund } from "./refunds";
import type { SettlementFile } from "./settlement";

export interface RailSummary { rail: string; payment_count: number; total_paise: number }
export type StatusCounts = Record<"CREATED" | "SUBMITTED" | "COMPLETED" | "FAILED" | "REFUNDED", number>;
export interface Dashboard {
  date: string;
  rails: RailSummary[];
  status_counts: StatusCounts;
  pending_refunds: Refund[];
  settlement_files: SettlementFile[];
}

export function fetchDashboard(date: string): Promise<Dashboard> {
  return apiRequest<Dashboard>(`/dashboard/summary?date=${encodeURIComponent(date)}`);
}

/** Fetch one slice of the summary; a missing slice is a tile-level error. */
export async function fetchTile<K extends keyof Dashboard>(date: string, key: K): Promise<Dashboard[K]> {
  const slice = (await fetchDashboard(date))[key];
  if (slice === undefined || slice === null) throw new Error(`Missing ${key}`);
  return slice;
}
