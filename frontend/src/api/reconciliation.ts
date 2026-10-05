import { API_BASE_URL } from "../config/env";
import { apiRequest, authHeaders } from "./client";

export interface ReconCounts {
  matched: number;
  unmatched_internal: number;
  unmatched_external: number;
  amount_mismatch: number;
}

export interface ReconResult {
  id: string;
  rail: string | null;
  status: string;
  payment_amount_paise: number | null;
  statement_amount_paise: number | null;
}

export async function runReconciliation(statementDate: string): Promise<ReconCounts> {
  const res = await apiRequest<{ counts: ReconCounts }>("/reconciliation/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ statement_date: statementDate }),
  });
  return res.counts;
}

export async function fetchUnmatched(): Promise<ReconResult[]> {
  return (await apiRequest<{ items: ReconResult[] }>("/reconciliation/unmatched")).items;
}

export async function resolveResult(id: string, note: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/reconciliation/${id}/resolve`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
}
