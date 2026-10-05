import { useState } from "react";
import { fetchUnmatched, resolveResult, runReconciliation } from "../../api/reconciliation";
import type { ReconCounts, ReconResult } from "../../api/reconciliation";
import { Dialog } from "../components/Dialog";
import { FieldError } from "../components/FieldError";
import { MoneyText } from "../components/MoneyText";
import { RetryBanner } from "../components/RetryBanner";
import { SkeletonRows } from "../components/Skeleton";
import { useResource } from "../hooks/useResource";

function Amount({ paise }: { paise: number | null }) {
  return paise === null ? <span>-</span> : <MoneyText paise={paise} />;
}

function RunForm({ onDone }: { onDone: () => void }) {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [counts, setCounts] = useState<ReconCounts | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      setCounts(await runReconciliation(date));
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  return (
    <section className="card">
      <form onSubmit={run} className="row">
        <div className="field">
          <label htmlFor="statement-date">Statement date</label>
          <input id="statement-date" type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <button type="submit" className="btn">Run reconciliation</button>
      </form>
      {error ? <div className="banner error" role="alert">{`Run failed: ${error}`}</div> : null}
      {counts ? (
        <dl className="kv" aria-label="Run summary">
          {Object.entries(counts).map(([status, n]) => (
            <div key={status} style={{ display: "contents" }}><dt>{status}</dt><dd>{n}</dd></div>
          ))}
        </dl>
      ) : null}
    </section>
  );
}

function ResolveDialog({ row, onClose, onResolved }: { row: ReconResult; onClose: () => void; onResolved: () => void }) {
  const [note, setNote] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!note.trim()) return setFieldError("A note is required");
    setFieldError(null);
    try {
      await resolveResult(row.id, note.trim());
      onResolved();
    } catch {
      setFailure("Could not resolve. Please try again.");
    }
  }

  return (
    <Dialog title="Resolve result" onClose={onClose}>
      <form onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="resolve-note">Resolution note</label>
          <textarea id="resolve-note" className="input" value={note} onChange={(e) => setNote(e.target.value)}
            aria-invalid={fieldError ? true : undefined} aria-describedby="resolve-note-error" />
          <FieldError id="resolve-note-error" message={fieldError} />
        </div>
        {failure ? <div className="banner error" role="alert">{failure}</div> : null}
        <div className="actions">
          <button type="button" className="btn secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn">Resolve</button>
        </div>
      </form>
    </Dialog>
  );
}

export function ReconciliationPage() {
  const { data, error, loading, refetch } = useResource(fetchUnmatched);
  const [active, setActive] = useState<ReconResult | null>(null);
  const [removed, setRemoved] = useState<string[]>([]);
  const rows = (data ?? []).filter((r) => !removed.includes(r.id));

  return (
    <div className="stack">
      <div className="page-head"><h1>Reconciliation</h1></div>
      <RunForm onDone={refetch} />
      {error ? <RetryBanner message={`Could not load unmatched results: ${error}`} onRetry={refetch} /> : null}
      {!error && !loading && rows.length === 0 ? <div className="card empty"><h2>Nothing to reconcile</h2></div> : null}
      {!error && (loading || rows.length > 0) ? (
        <section className="card flush">
          <table className="data">
            <caption>Unmatched results</caption>
            <thead>
              <tr>
                <th scope="col">Status</th><th scope="col">Rail</th>
                <th scope="col" className="num">Payment amount</th><th scope="col" className="num">Statement amount</th>
                <th scope="col"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {loading ? <SkeletonRows cols={5} rows={3} /> : rows.map((r) => (
                <tr key={r.id} data-id={r.id}>
                  <td>{r.status}</td>
                  <td>{r.rail ?? "-"}</td>
                  <td className="num"><Amount paise={r.payment_amount_paise} /></td>
                  <td className="num"><Amount paise={r.statement_amount_paise} /></td>
                  <td><button type="button" className="btn secondary sm" onClick={() => setActive(r)}>Resolve</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
      {active ? (
        <ResolveDialog row={active} onClose={() => setActive(null)}
          onResolved={() => { setRemoved((x) => [...x, active.id]); setActive(null); }} />
      ) : null}
    </div>
  );
}
