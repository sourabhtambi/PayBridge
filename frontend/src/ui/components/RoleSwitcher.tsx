import { useCallback, useEffect, useState } from "react";
import { fetchCustomers } from "../../api/customers";
import { ROLES } from "../../config/constants";
import type { Customer, Role } from "../../types/domain";
import { useSession } from "../state/SessionContext";

export function RoleSwitcher() {
  const { session, setRole, setCustomerId } = useSession();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const isCustomer = session.role === "customer";

  const load = useCallback(() => {
    setStatus("loading");
    fetchCustomers()
      .then((items) => { setCustomers(items); setStatus("ready"); })
      .catch(() => setStatus("error"));
  }, []);

  useEffect(() => {
    if (isCustomer) load();
  }, [isCustomer, load]);

  return (
    <div className="session">
      <label>
        Role
        <select value={session.role} onChange={(e) => setRole(e.target.value as Role)}>
          {ROLES.map((r) => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </select>
      </label>
      {isCustomer && (
        <label>
          Customer
          <select value={session.customerId ?? ""} disabled={status !== "ready"} onChange={(e) => setCustomerId(e.target.value)}>
            {status === "loading" && <option>Loading customers…</option>}
            {customers.map((c) => (
              <option key={c.id} value={c.id}>{`${c.name} (${c.id})`}</option>
            ))}
          </select>
        </label>
      )}
      {isCustomer && status === "error" && (
        <div className="banner error" role="alert">
          <span>Could not load customers. The customer picker is unavailable.</span>
          <button type="button" onClick={load}>Retry</button>
        </div>
      )}
    </div>
  );
}
