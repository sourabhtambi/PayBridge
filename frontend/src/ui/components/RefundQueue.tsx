import { useState } from "react";
import { RefundDecisionError, decideRefund, fetchRequestedRefunds } from "../../api/refunds";
import type { Refund } from "../../api/refunds";
import { MoneyText } from "./MoneyText";
import { RetryBanner } from "./RetryBanner";
import { SkeletonRows } from "./Skeleton";
import { useResource } from "../hooks/useResource";

const ALREADY_DECIDED = "This refund was already decided";

export function RefundQueue() {
  const { data, error, loading, refetch } = useResource(fetchRequestedRefunds);
  const [decided, setDecided] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState<string | null>(null);

  async function decide(r: Refund, action: "approve" | "reject") {
    setNotice(null);
    try {
      const updated = await decideRefund(r.id, action);
      setDecided((d) => ({ ...d, [r.id]: updated.state }));
    } catch (e) {
      setNotice(e instanceof RefundDecisionError && e.status === 409 ? ALREADY_DECIDED : "Something went wrong. Please try again.");
    }
  }

  const rows = data ?? [];
  return (
    <div className="stack">
      <div className="page-head"><h1>Refund queue</h1></div>
      {error ? <RetryBanner message={`Could not load refunds: ${error}`} onRetry={refetch} /> : null}
      {notice ? <div className="banner error" role="alert">{notice}</div> : null}
      {!error && !loading && rows.length === 0 ? <div className="card empty"><h2>No refunds pending</h2></div> : null}
      {!error && (loading || rows.length > 0) ? (
        <section className="card flush">
          <table className="data">
            <caption>Requested refunds</caption>
            <thead>
              <tr>
                <th scope="col">Refund</th><th scope="col">Payment</th>
                <th scope="col" className="num">Amount</th><th scope="col">Requested by</th>
                <th scope="col">State</th><th scope="col">Decision</th>
              </tr>
            </thead>
            <tbody>
              {loading ? <SkeletonRows cols={6} rows={3} /> : rows.map((r) => (
                <tr key={r.id} data-id={r.id}>
                  <td className="mono">{r.id}</td>
                  <td className="mono">{r.payment_id}</td>
                  <td className="num"><MoneyText paise={r.amount_paise} /></td>
                  <td className="mono">{r.requested_by}</td>
                  <td>{decided[r.id] ?? r.state}</td>
                  <td>
                    {decided[r.id] ? null : (
                      <div className="row">
                        <button type="button" className="btn sm" onClick={() => void decide(r, "approve")}>
                          Approve<span className="sr-only"> refund for payment {r.payment_id}</span>
                        </button>
                        <button type="button" className="btn danger sm" onClick={() => void decide(r, "reject")}>
                          Reject<span className="sr-only"> refund for payment {r.payment_id}</span>
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </div>
  );
}
