import { apiRequest } from "./client";
import type { Customer } from "../types/domain";
import type { CustomerList } from "../types/api";

export async function fetchCustomers(): Promise<Customer[]> {
  return (await apiRequest<CustomerList>("/customers")).items;
}
