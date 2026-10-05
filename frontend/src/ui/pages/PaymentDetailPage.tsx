import { useState } from "react";
import { getPayment } from "../../api/payments";
import { requestRefund } from "../../api/refunds";
import { loadSession } from "../../api/client";
import { formatCreated } from "../../service/format";
import { MoneyText } from "../components/MoneyText";
import { RetryBanner } from "../components/RetryBanner";
import { StateBadge } from "../components/StateBadge";
import { usePolling } from "../hooks/usePolling";
import type { PaymentDetail, PaymentRefund } from "../../types/domain";

export const POLL_MS = 2000;
const active = (d: PaymentDetail): boolean => d.state === "CREATED" || d.state === "SUBMITTED";

export const REFUND_EXISTS_MSG = "A refund was already requested for this payment";

function RefundSection({ p }: { p: PaymentDetail }) {
  const [refund, setRefund] = useState<PaymentRefund | null>(p.refund ?? null);
  const [pending, setPending] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const current = refund ?? p.refund ?? null;
  const canRequest = p.state === "COMPLETED" && !current && loadSession().role === "customer";
  const request = async (): Promise<void> => {
    setPending(true); setErr(null);
    try {
      const status = await requestRefund(p.id);
      if (status === 201) setRefund({ id: "", state: "REQUESTED", reason_code: null });
      else setErr(status === 409 ? REFUND_EXISTS_MSG : "Something went wrong. Please try again.");
    } catch {
      setErr("Something went wrong. Please try again.");
    }
    setPending(false);
  };
  return (
    <>
      {current ? (
        <div data-field="refund">
          <span className="badge" data-refund={current.state}>{current.state}</span>
          {current.state === "REQUESTED" ? <p><strong>Refund requested</strong></p> : null}
          {current.state === "REJECTED" || current.state === "FAILED" ? (
            <p data-field="refund.reason_code">Reason code: <span className="mono">{current.reason_code}</span></p>
          ) : null}
        </div>
      ) : null}
      {canRequest ? (
        <button type="button" className="btn secondary" disabled={pending} aria-busy={pending} onClick={() => { void request(); }}>
          Request refund
        </button>
      ) : null}
      <div role="alert">{err ? <div className="banner error">{err}</div> : null}</div>
    </>
  );
}

function Detail({ p }: { p: PaymentDetail }) {
  const events = [...p.events].sort((a, b) => a.at.localeCompare(b.at));
  return (
    <>
      <section className="card">
        <dl className="kv">
          <dt>Payment</dt><dd className="mono">{p.id}</dd>
          <dt>Amount</dt><dd><MoneyText paise={p.amount_paise} /></dd>
          <dt>Rail</dt><dd>{p.rail}</dd>
          <dt>Beneficiary</dt><dd>{p.beneficiary}</dd>
          <dt>State</dt><dd><StateBadge state={p.state} /></dd>
          <dt>Created</dt><dd><time dateTime={p.created_at}>{formatCreated(p.created_at)}</time></dd>
        </dl>
        {p.state === "FAILED" ? (
          <div className="banner error" role="note">Payment failed. Reason code: <span className="mono">{p.reason_code}</span></div>
        ) : null}
        <RefundSection p={p} />
      </section>
      <section className="card">
        <h2>Timeline</h2>
        <ol className="timeline" aria-label="Timeline">
          {events.map((e) => (
            <li key={e.id}><span>{e.type}</span> <time dateTime={e.at}>{formatCreated(e.at)}</time></li>
          ))}
        </ol>
      </section>
      <section className="card flush">
        <table className="data">
          <caption>Attempts</caption>
          <thead><tr><th scope="col">Attempt</th><th scope="col">Outcome</th></tr></thead>
          <tbody>
            {p.attempts.map((a) => (
              <tr key={a.attempt_no}><td>{a.attempt_no}</td><td>{a.outcome}{a.error_code ? ` (${a.error_code})` : ""}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

function SkeletonTimeline() {
  return (
    <section className="card" aria-busy="true" data-testid="skeleton-timeline">
      {[0, 1, 2].map((i) => <span key={i} className={`skel ${i % 2 ? "w60" : ""}`} />)}
    </section>
  );
}

export function PaymentDetailPage({ id }: { id: string }) {
  const { data, error, loading, refetch } = usePolling(() => getPayment(id), active, POLL_MS);
  const notFound = error === "Request failed: 404";
  return (
    <div className="stack">
      <div className="page-head"><h1>Payment</h1></div>
      {notFound ? (
        <div className="card empty"><h2>Payment not found</h2><a className="btn" href="/payments">Back to payments</a></div>
      ) : null}
      {error && !notFound ? <RetryBanner message={`Could not load this payment: ${error}`} onRetry={refetch} /> : null}
      {loading && !data ? <SkeletonTimeline /> : null}
      {data && !notFound ? <Detail p={data} /> : null}
    </div>
  );
}
