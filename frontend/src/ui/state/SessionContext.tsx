import { createContext, useContext, useState, type ReactNode } from "react";
import { loadSession, saveSession } from "../../api/client";
import type { Role, Session } from "../../types/domain";

interface SessionValue {
  session: Session;
  setRole: (role: Role) => void;
  setCustomerId: (id: string) => void;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session>(loadSession);
  const update = (next: Session) => {
    saveSession(next);
    setSession(next);
  };
  const value: SessionValue = {
    session,
    setRole: (role) => update({ role, customerId: session.customerId ?? "cus_001" }),
    setCustomerId: (customerId) => update({ ...session, customerId }),
  };
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
