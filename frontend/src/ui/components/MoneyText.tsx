import { formatRupees } from "../../service/format";

export function MoneyText({ paise }: { paise: number }) {
  return <span className="money">{formatRupees(paise)}</span>;
}
