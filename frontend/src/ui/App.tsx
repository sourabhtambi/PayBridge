import { useEffect, useRef, useState } from "react";
import { SessionProvider, useSession } from "./state/SessionContext";
import { AppShell } from "./components/AppShell";
import { NewPaymentPage } from "./pages/NewPaymentPage";
import { PaymentDetailPage } from "./pages/PaymentDetailPage";
import { PaymentsListPage } from "./pages/PaymentsListPage";
import { SimulationPage } from "./pages/SimulationPage";
import { RefundQueue } from "./components/RefundQueue";
import { ReconciliationPage } from "./pages/ReconciliationPage";
import { StuckPaymentsPage } from "./pages/StuckPaymentsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { SettlementPage } from "./pages/SettlementPage";
import { takeFlash } from "../service/flash";
import { usePathname } from "./hooks/usePathname";
import { navigate } from "./hooks/navigate";
import { DEFAULT_ROUTE_BY_ROLE } from "../config/routes";

function FlashBanner() {
  const [flash, setFlash] = useState<string | null>(null);
  const taken = useRef(false);
  useEffect(() => {
    if (taken.current) return;
    taken.current = true;
    setFlash(takeFlash());
  }, []);
  return flash ? <div className="banner success" role="status">{flash}</div> : null;
}

function Routes() {
  const path = usePathname();
  const { session } = useSession();
  const previousRole = useRef(session.role);
  useEffect(() => {
    if (previousRole.current === session.role) return;
    previousRole.current = session.role;
    navigate(DEFAULT_ROUTE_BY_ROLE[session.role]);
  }, [session.role]);
  const previousCustomer = useRef(session.customerId);
  useEffect(() => {
    if (previousCustomer.current === session.customerId) return;
    previousCustomer.current = session.customerId;
    if (path.startsWith("/payments/") && path !== "/payments/new") navigate("/payments");
  }, [session.customerId, path]);
  return (
    <AppShell>
      {path === "/payments" ? <PaymentsListPage key={session.customerId ?? ""} /> : null}
      {path === "/simulation" ? <SimulationPage /> : null}
      {path === "/dashboard" ? <DashboardPage /> : null}
      {path === "/refunds" ? <RefundQueue /> : null}
      {path === "/reconciliation" ? <ReconciliationPage /> : null}
      {path === "/stuck-payments" ? <StuckPaymentsPage /> : null}
      {path === "/settlement" ? <SettlementPage /> : null}
      {path === "/payments/new" ? <NewPaymentPage /> : null}
      {path.startsWith("/payments/") && path !== "/payments/new" ? (
        <>
          <FlashBanner />
          <PaymentDetailPage id={path.slice("/payments/".length)} />
        </>
      ) : null}
    </AppShell>
  );
}

export function App() {
  return (
    <SessionProvider>
      <Routes />
    </SessionProvider>
  );
}
