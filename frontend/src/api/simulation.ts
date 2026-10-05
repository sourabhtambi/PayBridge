import { apiRequest } from "./client";

export type SimMode = "success" | "permanent_failure" | "transient";
export interface RailSimulation {
  rail: string;
  mode: SimMode;
  reason_code: string | null;
  transient_failure_rate: number;
}

export async function fetchSimulation(): Promise<RailSimulation[]> {
  return (await apiRequest<{ items: RailSimulation[] }>("/admin/simulation")).items;
}

export function saveSimulation(c: RailSimulation): Promise<RailSimulation> {
  const { mode, reason_code, transient_failure_rate } = c;
  return apiRequest<RailSimulation>(`/admin/simulation/${c.rail}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, reason_code, transient_failure_rate }),
  });
}
