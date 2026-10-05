import type { Customer } from "./domain";
export interface ListResponse<T> { items: T[]; total: number }
export type CustomerList = ListResponse<Customer>;
import type { Payment } from "./domain";
export type PaymentList = ListResponse<Payment>;
