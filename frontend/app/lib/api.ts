/**
 * API client — all fetch calls go here, never inline in components.
 * Uses NEXT_PUBLIC_API_URL from environment.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) url.searchParams.set(k, String(v));
    });
  }
  const res = await fetch(url.toString(), { next: { revalidate: 300 } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

// --- Overview / Breadth ---

export const api = {
  overview: {
    latest: (universe = "all") => get<Record<string, unknown>>("/api/overview", { universe }),
    history: (days = 252, universe = "all") =>
      get<Record<string, unknown>[]>("/api/overview/history", { days, universe }),
  },

  breadth: {
    history: (days = 60, universe = "all") =>
      get<Record<string, unknown>[]>("/api/breadth/history", { days, universe }),
    ratios: (universe = "all") =>
      get<Record<string, unknown>>("/api/breadth/ratios", { universe }),
  },

  breakouts: {
    latest: (universe = "all") => get<Record<string, unknown>>("/api/breakouts", { universe }),
  },

  movers: {
    topN: (n = 20) => get<{ gainers: unknown[]; losers: unknown[] }>("/api/movers", { n }),
    extreme: (universe = "all") => get<Record<string, unknown>>("/api/movers/extreme", { universe }),
    volume: (n = 20) => get<unknown[]>("/api/movers/volume", { n }),
    momentum: (metric_type: string, universe = "all") =>
      get<Record<string, unknown>>("/api/movers/momentum", { metric_type, universe }),
  },

  sectors: {
    all: () => get<unknown[]>("/api/sectors"),
    byName: (name: string, n = 50) => get<unknown[]>(`/api/sectors/${encodeURIComponent(name)}`, { n }),
  },

  indexes: {
    latest: (universe = "all") => get<Record<string, unknown>>("/api/indexes", { universe }),
    history: (ticker: string, days = 252) =>
      get<unknown[]>("/api/indexes/history", { ticker, days }),
  },

  stock: {
    detail: (ticker: string) => get<Record<string, unknown>>(`/api/stock/${ticker}`),
    bars: (ticker: string, days = 252) => get<unknown[]>(`/api/stock/${ticker}/bars`, { days }),
  },

  repos: {
    list: () => get<unknown[]>("/api/repos"),
    columns: (repoId: string) => get<unknown[]>(`/api/repos/${repoId}/columns`),
    data: (
      repoId: string,
      metrics: string[],
      options?: { days?: number; universe?: string; group_by?: string }
    ) =>
      get<Record<string, unknown>[]>(`/api/repos/${repoId}/data`, {
        metrics: metrics.join(","),
        days: options?.days,
        universe: options?.universe,
        group_by: options?.group_by,
      }),
  },

  status: () => get<Record<string, unknown>>("/api/status"),
};
