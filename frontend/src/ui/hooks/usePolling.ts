import { useCallback, useEffect, useState } from "react";
import type { Resource } from "./useResource";

export function usePolling<T>(load: () => Promise<T>, keepPolling: (d: T) => boolean, intervalMs: number): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const run = (): void => {
      load()
        .then((d) => {
          if (!live) return;
          setData(d); setError(null); setLoading(false);
          if (keepPolling(d)) timer = setTimeout(run, intervalMs);
        })
        .catch((e: unknown) => {
          if (live) { setError(e instanceof Error ? e.message : "Unknown error"); setLoading(false); }
        });
    };
    setLoading(true);
    run();
    return () => { live = false; clearTimeout(timer); };
  }, [tick]);
  const refetch = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, refetch };
}
