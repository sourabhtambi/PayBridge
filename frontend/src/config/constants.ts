import type { Role } from "../types/domain";
export const SESSION_STORAGE_KEY = "paybridge.session";
export const ROLES: { value: Role; label: string }[] = [
  { value: "customer", label: "Customer" },
  { value: "ops", label: "Ops" },
  { value: "admin", label: "Admin" },
];
