import { fetchStuckPayments } from "../../api/ops";
import { MoneyText } from "../components/MoneyText";
import { RetryBanner } from "../components/RetryBanner";
import { useResource } from "../hooks/useResource";

export function formatAge(seconds: number): string {
  const m = Math.floor(seconds / 60);
  return m < 60 ? `${m}m` : `${Math.floor(m / 60)}h ${m % 60}m`;
}

export function StuckPaymentsPage() {
  const { data, error, loading, refetch } = useResource(fetchStuckPayments);
  return (
    <div className="stack">
      <div className="page-head"><h1>Stuck payments</h1></div>
      {error ? <RetryBanner message={`Could not load stuck payments: ${error}`} onRetry={refetch} /> : null}
      {!error && !loading && data?.length === 0 ? <div className="card empty"><h2>No stuck payments</h2></div> : null}
      {!error && data && data.length > 0 ? (
        <section className="card flush">
          <table className="data">
            <caption>Stuck payments</caption>
            <thead>
              <tr>
                <th scope="col">Payment</th><th scope="col">Rail</th>
                <th scope="col" className="num">Amount</th><th scope="col">Age</th>
              </tr>
            </thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.payment_id} data-id={p.payment_id}>
                  <td className="mono">{p.payment_id}</td>
                  <td>{p.rail}</td>
                  <td className="num"><MoneyText paise={p.amount_paise} /></td>
                  <td>{formatAge(p.age_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </div>
  );
}
