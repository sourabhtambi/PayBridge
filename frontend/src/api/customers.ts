import { apiRequest } from "./client";
import type { Customer } from "../types/domain";
import type { CustomerList } from "../types/api";

export async function fetchCustomers(): Promise<Customer[]> {
  const { items } = await apiRequest<CustomerList>("/customers");
  return items.filter((c) => c.role === "customer");
}
