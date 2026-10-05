import { useState } from "react";
import { createPayment } from "../../api/payments";
import { AMOUNT_MIN_MESSAGE, CONFLICT_MESSAGE, GENERIC_ERROR_MESSAGE, REPLAY_MESSAGE } from "../../service/errorMessages";
import { parseRupeesToPaise } from "../../service/money";
import { setFlash } from "../../service/flash";
import { navigate } from "../hooks/navigate";
import { previewRail } from "../../service/railPreview";
import { validateAmount, validateBeneficiary } from "../../service/validation";
import { FieldError } from "../components/FieldError";

const ID_PATTERN = /^[A-Za-z0-9_-]+$/;

interface Notice { kind: "error" | "success"; text: string }

export function NewPaymentPage() {
  const [amount, setAmount] = useState("");
  const [beneficiary, setBeneficiary] = useState("");
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [amountErr, setAmountErr] = useState<string | null>(null);
  const [benErr, setBenErr] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [pending, setPending] = useState(false);
  const rail = previewRail(amount);

  function onAmount(v: string) {
    setAmount(v);
    setAmountErr(v.trim() === "" ? null : validateAmount(v));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const aErr = validateAmount(amount);
    const bErr = validateBeneficiary(beneficiary);
    setAmountErr(aErr);
    setBenErr(bErr);
    const paise = parseRupeesToPaise(amount);
    if (aErr || bErr || paise === null) return;
    setPending(true);
    setNotice(null);
    try {
      const r = await createPayment(paise, beneficiary.trim(), key);
      handleResult(r.status, r.id);
    } catch {
      setNotice({ kind: "error", text: GENERIC_ERROR_MESSAGE });
    } finally {
      setPending(false);
    }
  }

  function handleResult(status: number, id?: string) {
    if ((status === 202 || status === 200) && !(id && ID_PATTERN.test(id))) {
      setNotice({ kind: "error", text: GENERIC_ERROR_MESSAGE });
    } else if (status === 202 && id) {
      setKey(crypto.randomUUID());
      navigate(`/payments/${id}`);
    } else if (status === 200 && id) {
      setFlash(REPLAY_MESSAGE);
      navigate(`/payments/${id}`);
    } else if (status === 409) setNotice({ kind: "error", text: CONFLICT_MESSAGE });
    else if (status === 422) setAmountErr(AMOUNT_MIN_MESSAGE);
    else setNotice({ kind: "error", text: GENERIC_ERROR_MESSAGE });
  }

  return (
    <>
      <h1>New payment</h1>
      <form className="card stack" onSubmit={submit} noValidate aria-label="New payment">
        <div className="field">
          <label htmlFor="amount">Amount (Rs)</label>
          <input id="amount" className="input" inputMode="decimal" autoComplete="off" value={amount}
            aria-invalid={amountErr ? true : undefined} aria-describedby="amount-err"
            onChange={(e) => onAmount(e.target.value)} />
          <FieldError id="amount-err" message={amountErr} />
        </div>
        <div className="field">
          <label htmlFor="beneficiary">Beneficiary</label>
          <input id="beneficiary" className="input" maxLength={140} autoComplete="off" value={beneficiary}
            aria-invalid={benErr ? true : undefined} aria-describedby="ben-err"
            onChange={(e) => setBeneficiary(e.target.value)} />
          <FieldError id="ben-err" message={benErr} />
        </div>
        <div className="field">
          <label htmlFor="idem">Idempotency key</label>
          <input id="idem" className="input mono" readOnly value={key} />
        </div>
        {notice && <div className={`banner ${notice.kind}`} role={notice.kind === "error" ? "alert" : "status"}>{notice.text}</div>}
        <button type="submit" className="btn" disabled={pending}>{pending ? "Submitting…" : "Pay"}</button>
      </form>
      <section className="card" aria-labelledby="rp-h">
        <h2 id="rp-h">Rail preview</h2>
        <div role="status" aria-live="polite" data-testid="rail-preview" data-rail={rail ?? "none"}>
          {rail ? <p>This payment will be routed via <strong>{rail}</strong></p> : <p><strong>No rail</strong></p>}
        </div>
      </section>
    </>
  );
}
