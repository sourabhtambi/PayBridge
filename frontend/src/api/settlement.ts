import { API_BASE_URL } from "../config/env";
import { apiRequest, authHeaders } from "./client";

export interface SettlementFile {
  id: string;
  business_date: string;
  kind: "primary" | "followup";
  row_count: number;
  checksum: string;
  written_at: string;
}

export interface SettlementRunResult {
  file: SettlementFile | null;
  message: string;
}

export async function fetchSettlementFiles(): Promise<SettlementFile[]> {
  return (await apiRequest<{ items: SettlementFile[] }>("/settlement/files")).items;
}

export function runSettlement(): Promise<SettlementRunResult> {
  return apiRequest<SettlementRunResult>("/settlement/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export async function downloadSettlementCsv(file: SettlementFile): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/settlement/files/${file.id}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = `${file.business_date}-${file.kind}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
