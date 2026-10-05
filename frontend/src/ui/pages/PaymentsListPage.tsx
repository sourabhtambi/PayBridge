import { listPayments } from "../../api/payments";
import { formatCreated } from "../../service/format";
import { EmptyState } from "../components/EmptyState";
import { MoneyText } from "../components/MoneyText";
import { RetryBanner } from "../components/RetryBanner";
import { SkeletonRows } from "../components/Skeleton";
import { StateBadge } from "../components/StateBadge";
import { useResource } from "../hooks/useResource";
import type { Payment } from "../../types/domain";

const HEADERS = ["Payment", "Amount", "Rail", "State", "Reason code", "Created"];

function Row({ p }: { p: Payment }) {
  return (
    <tr data-id={p.id}>
      <td><a className="mono" href={`/payments/${p.id}`}>{p.id}</a></td>
      <td className="num"><MoneyText paise={p.amount_paise} /></td>
      <td>{p.rail}</td>
      <td><StateBadge state={p.state} /></td>
      <td className="mono">{p.state === "FAILED" && p.reason_code ? p.reason_code : "—"}</td>
      <td><time dateTime={p.created_at}>{formatCreated(p.created_at)}</time></td>
    </tr>
  );
}

export function PaymentsListPage() {
  const { data, error, loading, refetch } = useResource(listPayments);
  return (
    <div className="stack">
      <div className="page-head">
        <h1>My payments</h1>
        <a className="btn" href="/payments/new">New payment</a>
      </div>
      {error ? <RetryBanner message={`Could not load your payments: ${error}`} onRetry={refetch} /> : null}
      {!error && !loading && data?.items.length === 0 ? (
        <EmptyState title="No payments yet" actionHref="/payments/new" actionLabel="Create your first payment" />
      ) : null}
      {!error && (loading || (data && data.items.length > 0)) ? (
        <section className="card flush" aria-busy={loading}>
          <table className="data">
            <caption>My payments</caption>
            <thead>
              <tr>{HEADERS.map((h) => <th key={h} scope="col" className={h === "Amount" ? "num" : undefined}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {loading ? <SkeletonRows cols={HEADERS.length} rows={5} /> : data?.items.map((p) => <Row key={p.id} p={p} />)}
            </tbody>
          </table>
        </section>
      ) : null}
    </div>
  );
}
