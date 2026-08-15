export function OrbitalLoader({ label = "Loading" }: { label?: string }) {
  return (
    <div className="orbital" role="status" aria-label={label}>
      <div className="orbit"><span className="electron" /></div>
      <div className="orbit"><span className="electron" /></div>
      <div className="orbit"><span className="electron" /></div>
      <div className="nucleus" />
    </div>
  );
}

export function BootScreen() {
  return (
    <div className="boot-screen">
      <div style={{ textAlign: "center" }}>
        <OrbitalLoader label="Starting OpenGero" />
        <div className="serif" style={{ fontSize: "1.8rem" }}>OpenGero</div>
        <p className="muted">Warming the screening workbench…</p>
      </div>
    </div>
  );
}

export function PageLoader({ label = "Loading workspace" }: { label?: string }) {
  return (
    <div className="page-loader">
      <OrbitalLoader label={label} />
      <div className="muted">{label}</div>
    </div>
  );
}

export function SkeletonLines({ rows = 4 }: { rows?: number }) {
  return (
    <div>
      <div className="skeleton sk-title" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton sk-line" style={{ width: `${88 - i * 8}%` }} />
      ))}
    </div>
  );
}

export function SkeletonCards({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card">
          <div className="skeleton sk-thumb" />
          <div className="skeleton sk-title" style={{ marginTop: 12 }} />
          <div className="skeleton sk-line" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 6 }: { rows?: number }) {
  return (
    <div className="table-wrap">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton sk-row" />
      ))}
    </div>
  );
}

export function ButtonSpinner() {
  return <span className="btn-spin" aria-hidden="true" />;
}
