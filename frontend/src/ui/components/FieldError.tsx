export function FieldError({ id, message }: { id: string; message: string | null }) {
  return message ? <span id={id} className="field-error" role="alert">{message}</span> : <span id={id} />;
}
