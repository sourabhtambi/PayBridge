import { API_BASE_URL } from "../config/env";
import { apiRequest, authHeaders, loadSession } from "./client";
import type { PaymentList } from "../types/api";
import type { PaymentDetail } from "../types/domain";

export interface CreatePaymentResult { status: number; id?: string }

export async function createPayment(
  amountPaise: number,
  beneficiary: string,
  idempotencyKey: string,
): Promise<CreatePaymentResult> {
  const res = await fetch(`${API_BASE_URL}/payments`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ amount_paise: amountPaise, beneficiary }),
  });
  if (res.status === 200 || res.status === 202) {
    const body = (await res.json()) as { id: string };
    return { status: res.status, id: body.id };
  }
  return { status: res.status };
}

export function listPayments(): Promise<PaymentList> {
  const { role, customerId } = loadSession();
  const query = role === "customer" && customerId ? `?customer_id=${encodeURIComponent(customerId)}` : "";
  return apiRequest<PaymentList>(`/payments${query}`);
}

export function getPayment(id: string): Promise<PaymentDetail> {
  return apiRequest<PaymentDetail>(`/payments/${encodeURIComponent(id)}`);
}
