import { useState } from "react";
import { fetchSimulation, saveSimulation } from "../../api/simulation";
import type { RailSimulation, SimMode } from "../../api/simulation";
import { FieldError } from "../components/FieldError";
import { RetryBanner } from "../components/RetryBanner";
import { useResource } from "../hooks/useResource";

const MODES: [SimMode, string][] = [["success", "Success"], ["permanent_failure", "Permanent failure"], ["transient", "Transient"]];
const REASONS = ["INSUFFICIENT_FUNDS", "INVALID_BENEFICIARY", "BENEFICIARY_ACCOUNT_CLOSED", "LIMIT_EXCEEDED"];

export function parseRate(text: string): number | null {
  const n = Number(text);
  return text.trim() !== "" && Number.isFinite(n) && n >= 0 && n <= 1 ? n : null;
}

function RailCard({ initial }: { initial: RailSimulation }) {
  const r = initial.rail;
  const [mode, setMode] = useState<SimMode>(initial.mode);
  const [reason, setReason] = useState(initial.reason_code ?? "");
  const [rate, setRate] = useState(String(initial.transient_failure_rate));
  const [rateErr, setRateErr] = useState<string | null>(null);
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setStatus(null);
    const parsed = parseRate(rate);
    if (parsed === null) { setRateErr("Enter a rate between 0 and 1"); return; }
    setRateErr(null);
    try {
      await saveSimulation({ rail: r, mode, reason_code: mode === "permanent_failure" ? reason || null : null, transient_failure_rate: parsed });
      setStatus({ ok: true, text: `Saved. ${r} simulation updated` });
    } catch (err) {
      setStatus({ ok: false, text: err instanceof Error ? err.message : "Save failed" });
    }
  }

  return (
    <form className="card stack" aria-label={`${r} simulation`} onSubmit={submit} noValidate>
      <h2>{r}</h2>
      <fieldset className="field">
        <legend>{r} mode</legend>
        {MODES.map(([v, label]) => (
          <div className="radio" key={v}>
            <input type="radio" id={`mode-${r}-${v}`} name={`mode-${r}`} value={v} checked={mode === v} onChange={() => setMode(v)} />
            <label htmlFor={`mode-${r}-${v}`}>{label}</label>
          </div>
        ))}
      </fieldset>
      <div className="field">
        <label htmlFor={`reason-${r}`}>Reason code (used for permanent failure)</label>
        <select className="input" id={`reason-${r}`} value={reason} onChange={(e) => setReason(e.target.value)}>
          <option value="">Select a reason code</option>
          {REASONS.map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor={`rate-${r}`}>Transient failure rate (0 to 1)</label>
        <input className="input" id={`rate-${r}`} inputMode="decimal" autoComplete="off" value={rate}
          aria-invalid={rateErr ? true : undefined} aria-describedby={`rate-err-${r}`} onChange={(e) => setRate(e.target.value)} />
        <FieldError id={`rate-err-${r}`} message={rateErr} />
      </div>
      <button type="submit" className="btn">Save {r}</button>
      {status ? <div className={`banner ${status.ok ? "success" : "error"}`} role={status.ok ? "status" : "alert"}>{status.text}</div> : null}
    </form>
  );
}

export function SimulationPage() {
  const { data, error, refetch } = useResource(fetchSimulation);
  return (
    <div className="stack">
      <div className="page-head"><h1>Simulation</h1></div>
      {error ? <RetryBanner message={`Could not load simulation: ${error}`} onRetry={refetch} /> : null}
      {data?.map((c) => <RailCard key={c.rail} initial={c} />)}
    </div>
  );
}
