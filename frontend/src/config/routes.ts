import type { NavItem, Role } from "../types/domain";
export const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  customer: [{ label: "Payments", route: "/payments" }],
  ops: [
    { label: "Reconciliation", route: "/reconciliation" },
    { label: "Stuck payments", route: "/stuck-payments" },
  ],
  admin: [
    { label: "Dashboard", route: "/dashboard" },
    { label: "Settlement", route: "/settlement" },
    { label: "Simulation", route: "/simulation" },
  ],
};

export const DEFAULT_ROUTE_BY_ROLE: Record<Role, string> = {
  customer: "/payments",
  ops: "/reconciliation",
  admin: "/dashboard",
};
