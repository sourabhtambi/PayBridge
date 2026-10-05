export function SkeletonRows({ cols, rows }: { cols: number; rows: number }) {
  return (
    <>
      {Array.from({ length: rows }, (_, r) => (
        <tr key={r} aria-hidden="true" data-testid="skeleton-row">
          {Array.from({ length: cols }, (_, c) => (
            <td key={c}><span className={`skel ${c % 2 ? "w60" : ""}`} /></td>
          ))}
        </tr>
      ))}
    </>
  );
}
