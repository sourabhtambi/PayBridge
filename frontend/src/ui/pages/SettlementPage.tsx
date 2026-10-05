import { useState } from "react";
import { downloadSettlementCsv, fetchSettlementFiles, runSettlement } from "../../api/settlement";
import type { SettlementFile } from "../../api/settlement";
import { RetryBanner } from "../components/RetryBanner";
import { SkeletonRows } from "../components/Skeleton";
import { useResource } from "../hooks/useResource";

function FileRow({ f, onError }: { f: SettlementFile; onError: (m: string) => void }) {
  const download = (e: React.MouseEvent) => {
    e.preventDefault();
    downloadSettlementCsv(f).catch((err: unknown) => onError(err instanceof Error ? err.message : "Download failed"));
  };
  return (
    <tr data-id={f.id}>
      <td>{f.business_date}</td>
      <td><span className={`badge ${f.kind === "primary" ? "info" : "neutral"}`}>{f.kind}</span></td>
      <td className="num">{f.row_count}</td>
      <td className="mono">{f.checksum}</td>
      <td>
        <a className="btn secondary sm" href={`/settlement/files/${f.id}`} onClick={download}
          aria-label={`Download CSV: ${f.kind} settlement file for ${f.business_date}`}>Download CSV</a>
      </td>
    </tr>
  );
}

export function SettlementPage() {
  const { data, error, loading, refetch } = useResource(fetchSettlementFiles);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);

  async function run() {
    setRunning(true);
    setResult(null);
    try {
      const r = await runSettlement();
      setResult({ ok: true, text: r.message });
      refetch();
    } catch (e) {
      setResult({ ok: false, text: e instanceof Error ? e.message : "Run failed" });
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="stack">
      <div className="page-head"><h1>Settlement</h1></div>
      <div className="card">
        <button type="button" className="btn" disabled={running} onClick={() => void run()}>Run now</button>
      </div>
      {result ? <div className={`banner ${result.ok ? "success" : "error"}`} role="status">{result.text}</div> : null}
      {error ? <RetryBanner message={`Could not load settlement files: ${error}`} onRetry={refetch} /> : null}
      {!error && !loading && data?.length === 0 ? <div className="card empty"><h2>No settlement files yet</h2></div> : null}
      {!error && (loading || (data && data.length > 0)) ? (
        <section className="card flush" aria-busy={loading}>
          <table className="data">
            <caption>Settlement files</caption>
            <thead>
              <tr>
                <th scope="col">Business date</th><th scope="col">Kind</th>
                <th scope="col" className="num">Rows</th><th scope="col">Checksum (sha256)</th>
                <th scope="col">Download</th>
              </tr>
            </thead>
            <tbody>
              {loading ? <SkeletonRows cols={5} rows={3} /> : data?.map((f) => (
                <FileRow key={f.id} f={f} onError={(m) => setResult({ ok: false, text: m })} />
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </div>
  );
}
