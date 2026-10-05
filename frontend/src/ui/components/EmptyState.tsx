export function EmptyState({ title, actionHref, actionLabel }: { title: string; actionHref: string; actionLabel: string }) {
  return (
    <div className="card empty">
      <h2>{title}</h2>
      <a className="btn" href={actionHref}>{actionLabel}</a>
    </div>
  );
}
