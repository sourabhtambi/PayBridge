import { API_BASE_URL } from "../config/env";
import { apiRequest, authHeaders } from "./client";

export async function requestRefund(paymentId: string): Promise<number> {
  const res = await fetch(`${API_BASE_URL}/refunds`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ payment_id: paymentId }),
  });
  return res.status;
}

export interface Refund {
  id: string;
  payment_id: string;
  amount_paise: number;
  state: string;
  requested_by: string;
}

export async function fetchRequestedRefunds(): Promise<Refund[]> {
  return (await apiRequest<{ items: Refund[] }>("/refunds?state=REQUESTED")).items;
}

export class RefundDecisionError extends Error {
  constructor(readonly status: number) {
    super(`Request failed: ${status}`);
  }
}

export async function decideRefund(id: string, action: "approve" | "reject"): Promise<Refund> {
  const res = await fetch(`${API_BASE_URL}/refunds/${id}/${action}`, { method: "POST", headers: authHeaders() });
  if (!res.ok) throw new RefundDecisionError(res.status);
  return (await res.json()) as Refund;
}
