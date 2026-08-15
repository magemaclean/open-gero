export const PAGE_SIZE = 50;

export function moleculeQuery(opts: {
  q?: string;
  mwMax?: string;
  mwMin?: string;
  tpsaMax?: string;
  logpMax?: string;
  lipinski?: boolean;
  veber?: boolean;
  deleted?: boolean;
  offset?: number;
  limit?: number;
}): URLSearchParams {
  const params = new URLSearchParams();
  if (opts.q) params.set("q", opts.q);
  if (opts.mwMax) params.set("mw_max", opts.mwMax);
  if (opts.mwMin) params.set("mw_min", opts.mwMin);
  if (opts.tpsaMax) params.set("tpsa_max", opts.tpsaMax);
  if (opts.logpMax) params.set("logp_max", opts.logpMax);
  if (opts.lipinski) params.set("lipinski", "true");
  if (opts.veber) params.set("veber", "true");
  if (opts.deleted) params.set("deleted", "true");
  params.set("limit", String(opts.limit ?? PAGE_SIZE));
  params.set("offset", String(opts.offset ?? 0));
  return params;
}

export function jobSocketUrl(
  jobId: string,
  token: string | null,
  loc: Pick<Location, "protocol" | "host"> = window.location,
): string {
  const proto = loc.protocol === "https:" ? "wss" : "ws";
  const qs = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${proto}://${loc.host}/api/ws/jobs/${jobId}${qs}`;
}

/** QED and other gauges must not render a fake 0.00 when the value is missing. */
export function formatMetric(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toFixed(value < 10 ? 2 : 1);
}
