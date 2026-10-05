import type { PaymentState } from "../../types/domain";

const STYLE: Record<PaymentState, [string, string]> = {
  CREATED: ["neutral", "○"], SUBMITTED: ["info", "◐"], COMPLETED: ["success", "✓"], FAILED: ["danger", "✕"],
  REFUNDED: ["warn", "↩"],
};

export function StateBadge({ state }: { state: PaymentState }) {
  const [tone, glyph] = STYLE[state] ?? ["neutral", "•"];
  return (
    <span className={`badge ${tone}`} data-state={state}>
      <span className="g" aria-hidden="true">{glyph}</span>{state}
    </span>
  );
}
