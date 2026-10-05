export function RetryBanner({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="banner error" role="alert">
      <span className="msg"><strong>Something went wrong.</strong> {message}</span>
      <button type="button" className="btn secondary sm" onClick={onRetry}>Retry</button>
    </div>
  );
}
