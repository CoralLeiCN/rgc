"use client";

import { useCallback, useEffect, useState } from "react";
import type { CohortQuery } from "../contracts";

export function cohortParams(cohort: CohortQuery) {
  const query = new URLSearchParams();
  if (cohort.search?.trim()) query.set("search", cohort.search.trim());
  if (cohort.source && cohort.source !== "all") query.set("source", cohort.source);
  if (cohort.role && cohort.role !== "all") query.set("role", cohort.role);
  if (cohort.status && cohort.status !== "all") query.set("status", cohort.status);
  if (cohort.rules?.length) query.set("rules", JSON.stringify(cohort.rules));
  return query;
}

export function useApi<T>(url: string | null) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{ url: string | null; attempt: number; data: T | null; loading: boolean; error: string | null }>({ url, attempt: 0, data: null, loading: Boolean(url), error: null });
  const retry = useCallback(() => setAttempt(value => value + 1), []);
  useEffect(() => {
    if (!url) {
      setState({ url, attempt, data: null, loading: false, error: null });
      return;
    }
    const controller = new AbortController();
    setState({ url, attempt, data: null, loading: true, error: null });
    void fetch(url, { signal: controller.signal, headers: { Accept: "application/json" } })
      .then(async response => {
        const body = await response.json();
        if (!response.ok) throw new Error(body?.error?.message || "This request could not be completed.");
        return body as T;
      })
      .then(data => { if (!controller.signal.aborted) setState({ url, attempt, data, loading: false, error: null }); })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ url, attempt, data: null, loading: false, error: error instanceof Error ? error.message : "The collection could not be loaded." });
      });
    return () => controller.abort();
  }, [url, attempt]);
  const current = state.url === url && state.attempt === attempt;
  return { data: current ? state.data : null, loading: current ? state.loading : Boolean(url), error: current ? state.error : null, retry };
}

export function useDebounced<T>(value: T, delay = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timeout);
  }, [value, delay]);
  return debounced;
}
