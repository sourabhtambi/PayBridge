export type Role = "customer" | "ops" | "admin";
export interface Customer { id: string; name: string; role: string }
export interface Session { role: Role; customerId: string | null }
export interface NavItem { label: string; route: string }
export type PaymentState = "CREATED" | "SUBMITTED" | "COMPLETED" | "FAILED" | "REFUNDED";
export interface Payment {
  id: string;
  customer_id: string;
  amount_paise: number;
  rail: string;
  beneficiary: string;
  state: PaymentState;
  reason_code: string | null;
  refund?: PaymentRefund | null;
  created_at: string;
}
export interface PaymentRefund { id: string; state: string; reason_code: string | null }
export interface PaymentEventItem { id: string; type: string; payload: Record<string, unknown>; at: string }
export interface PaymentAttempt { attempt_no: number; outcome: string; error_code: string | null; at: string }
export interface PaymentDetail extends Payment { events: PaymentEventItem[]; attempts: PaymentAttempt[] }
