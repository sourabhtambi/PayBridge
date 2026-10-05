import { useState } from "react";
import type { ReactNode } from "react";
import { fetchTile } from "../../api/dashboard";
import type { Dashboard } from "../../api/dashboard";
import { RefundDecisionError, decideRefund } from "../../api/refunds";
import type { Refund } from "../../api/refunds";
import { MoneyText } from "../components/MoneyText";
import { RetryBanner } from "../components/RetryBanner";
import { useResource } from "../hooks/useResource";

const STATUSES = ["CREATED", "SUBMITTED", "COMPLETED", "FAILED", "REFUNDED"] as const;

export function todayIST(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
}

function Tile<K extends keyof Dashboard>(props: {
  date: string; slice: K; title: string; children: (d: Dashboard[K], refetch: () => void) => ReactNode;
}) {
  const { data, error, loading, refetch } = useResource(() => fetchTile(props.date, props.slice));
  return (
    <section className="card" data-tile={props.slice} aria-labelledby={`t-${props.slice}`}>
      <h2 id={`t-${props.slice}`}>{props.title}</h2>
      {error ? <RetryBanner message={`Could not load ${props.title.toLowerCase()}: ${error}`} onRetry={refetch} /> : null}
      {loading && !error ? <p className="muted" aria-busy="true">Loading...</p> : null}
      {!loading && !error && data !== null ? props.children(data, refetch) : null}
    </section>
  );
}

function RefundTile({ refunds }: { refunds: Refund[] }) {
  const [decided, setDecided] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState<string | null>(null);
  const pending = refunds.filter((r) => !decided[r.id]).length;

  async function decide(r: Refund, action: "approve" | "reject") {
    setNotice(null);
    try {
      const updated = await decideRefund(r.id, action);
      setDecided((d) => ({ ...d, [r.id]: updated.state }));
    } catch (e) {
      setNotice(e instanceof RefundDecisionError && e.status === 409 ? "This refund was already decided" : "Something went wrong. Please try again.");
    }
  }

  return (
    <>
      <p data-field="pending_count">{pending} pending</p>
      <p><a href="/refunds">Open full refund queue</a></p>
      {notice ? <div className="banner error" role="alert">{notice}</div> : null}
      {refunds.length === 0 ? <p>No refunds pending</p> : (
        <table className="data">
          <caption className="sr-only">Pending refunds</caption>
          <thead><tr><th scope="col">Payment</th><th scope="col" className="num">Amount</th><th scope="col">State</th><th scope="col">Decision</th></tr></thead>
          <tbody>
            {refunds.map((r) => (
              <tr key={r.id} data-id={r.id}>
                <td className="mono">{r.payment_id}</td>
                <td className="num"><MoneyText paise={r.amount_paise} /></td>
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
      )}
    </>
  );
}

function ActivityBanner({ date }: { date: string }) {
  const { data } = useResource(() => fetchTile(date, "rails"));
  const idle = data !== null && data.every((r) => r.payment_count === 0);
  return idle ? <div className="banner info" role="status" id="no-activity"><strong>No activity for this date</strong></div> : null;
}

export function DashboardPage() {
  const [date, setDate] = useState(todayIST);
  const today = todayIST();
  return (
    <div className="stack">
      <div className="page-head">
        <h1>Dashboard</h1>
        <div className="field">
          <label htmlFor="date">Date (IST)</label>
          <input className="input" type="date" id="date" value={date} max={today}
            onChange={(e) => setDate(e.target.value || today)} />
        </div>
      </div>
      <ActivityBanner key={`a-${date}`} date={date} />
      <Tile key={`r-${date}`} date={date} slice="rails" title="Volume by rail">
        {(rails) => (
          <div className="grid cols-4">
            {rails.map((r) => (
              <div className="tile" key={r.rail} data-rail={r.rail}>
                <div className="k">{r.rail}</div>
                <div className="v"><MoneyText paise={r.total_paise} /></div>
                <div className="s"><span data-field="payment_count">{r.payment_count}</span> payments</div>
              </div>
            ))}
          </div>
        )}
      </Tile>
      <Tile key={`s-${date}`} date={date} slice="status_counts" title="Status breakdown">
        {(sc) => (
          <div className="grid cols-4">
            {STATUSES.map((s) => (
              <div className="tile" key={s} data-status={s}>
                <div className="k">{s}</div>
                <div className="v" data-field={`status_counts.${s}`}>{sc[s]}</div>
              </div>
            ))}
          </div>
        )}
      </Tile>
      <Tile key={`p-${date}`} date={date} slice="pending_refunds" title="Refund queue">
        {(refunds) => <RefundTile refunds={refunds} />}
      </Tile>
      <Tile key={`f-${date}`} date={date} slice="settlement_files" title="Settlement reports">
        {(files) => files.length === 0 ? <p>No settlement files for this date</p> : (
          <table className="data">
            <caption className="sr-only">Settlement reports for {date}</caption>
            <thead><tr><th scope="col">Business date</th><th scope="col">Kind</th><th scope="col" className="num">Rows</th></tr></thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.id}><td>{f.business_date}</td><td>{f.kind}</td><td className="num">{f.row_count}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </Tile>
    </div>
  );
}
