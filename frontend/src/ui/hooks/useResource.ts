import { useCallback, useEffect, useState } from "react";

export interface Resource<T> { data: T | null; error: string | null; loading: boolean; refetch: () => void }

export function useResource<T>(load: () => Promise<T>): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    load()
      .then((d) => { if (live) { setData(d); setLoading(false); } })
      .catch((e: unknown) => { if (live) { setError(e instanceof Error ? e.message : "Unknown error"); setLoading(false); } });
    return () => { live = false; };
  }, [tick]);
  const refetch = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, refetch };
}
