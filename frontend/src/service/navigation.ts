import { NAV_BY_ROLE } from "../config/routes";
import type { NavItem, Role } from "../types/domain";
export function navItemsFor(role: Role): NavItem[] {
  return NAV_BY_ROLE[role];
}
