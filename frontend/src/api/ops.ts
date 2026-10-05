import { apiRequest } from "./client";

export interface StuckPayment {
  payment_id: string;
  rail: string;
  amount_paise: number;
  age_seconds: number;
}

export async function fetchStuckPayments(): Promise<StuckPayment[]> {
  return (await apiRequest<{ items: StuckPayment[] }>("/ops/stuck-payments")).items;
}
