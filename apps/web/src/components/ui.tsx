import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent, ReactNode } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { formatMetric } from "../lib/query";
import type { Crumb } from "../lib/nav";
import { IconMore } from "./icons";

export function cx(...parts: Array<string | false | undefined | null>) {
  return parts.filter(Boolean).join(" ");
}

export function useCountUp(value: number, duration = 700) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      setN(Math.round(value * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return n;
}

export function spotlightMove(e: MouseEvent<HTMLElement>) {
  const r = e.currentTarget.getBoundingClientRect();
  e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
  e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
}

export function PageHeader({
  kicker,
  title,
  subtitle,
  actions,
}: {
  kicker?: string;
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="page-head">
      <div>
        {kicker && <div className="page-kicker">{kicker}</div>}
        <h1>{title}</h1>
        {subtitle && <p style={{ marginBottom: 0 }}>{subtitle}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </header>
  );
}

export function Breadcrumbs({ crumbs }: { crumbs: Crumb[] }) {
  if (crumbs.length === 0) return null;
  return (
    <nav className="crumbs" aria-label="Breadcrumb">
      {crumbs.map((c, i) => {
        const last = i === crumbs.length - 1;
        return (
          <span key={`${c.label}-${i}`} className="crumbs-item">
            {i > 0 && <span className="crumbs-sep" aria-hidden="true">/</span>}
            {c.to && !last ? (
              <Link to={c.to}>{c.label}</Link>
            ) : (
              <span aria-current={last ? "page" : undefined}>{c.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}

export type ActionItem = { label: string; onClick: () => void; danger?: boolean; disabled?: boolean };

export function ActionMenu({ label = "Actions", items }: { label?: string; items: ActionItem[] }) {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  const place = useCallback(() => {
    const r = btnRef.current?.getBoundingClientRect();
    if (!r) return;
    const width = 200;
    setPos({
      top: r.bottom + 6,
      left: Math.min(window.innerWidth - width - 8, Math.max(8, r.right - width)),
    });
  }, []);

  useEffect(() => {
    if (!open) return;
    place();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open, place]);

  return (
    <div className="action-menu" onClick={(e) => e.stopPropagation()}>
      <button
        ref={btnRef}
        type="button"
        className="icon-btn secondary"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <IconMore />
      </button>
      {open &&
        createPortal(
          <>
            <div className="action-menu-scrim" onClick={() => setOpen(false)} />
            <div className="action-menu-list" role="menu" style={{ top: pos.top, left: pos.left }}>
              {items.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  role="menuitem"
                  className={item.danger ? "action-menu-item danger" : "action-menu-item"}
                  disabled={item.disabled}
                  onClick={() => {
                    setOpen(false);
                    item.onClick();
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </>,
          document.body,
        )}
    </div>
  );
}

export function EmptyState({ title, detail, action }: { title: string; detail: string; action?: ReactNode }) {
  return (
    <div className="card empty">
      <div className="empty-ico" aria-hidden="true">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="12" cy="12" r="8" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <h3>{title}</h3>
      <p>{detail}</p>
      {action}
    </div>
  );
}

export function StatCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  const numeric = typeof value === "number";
  const shown = useCountUp(numeric ? value : 0);
  return (
    <div className="card interactive" onMouseMove={spotlightMove}>
      <div className="muted">{label}</div>
      <div className="serif stat" style={{ fontSize: "1.7rem" }}>
        {numeric ? shown.toLocaleString() : value}
      </div>
      {hint && <div className="muted">{hint}</div>}
    </div>
  );
}

export function Gauge({ label, value, max, unit }: { label: string; value: number | null | undefined; max: number; unit?: string }) {
  if (value == null || !Number.isFinite(value)) {
    return (
      <div className="gauge">
        <div className="ring" style={{ ["--p" as string]: 0 }} />
        <div>
          <div className="muted">{label}</div>
          <strong className="mono">{formatMetric(value)}</strong>
        </div>
      </div>
    );
  }
  const p = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="gauge">
      <div className="ring" style={{ ["--p" as string]: p }} />
      <div>
        <div className="muted">{label}</div>
        <strong className="mono">
          {formatMetric(value)}
          {unit ? ` ${unit}` : ""}
        </strong>
      </div>
    </div>
  );
}

export function ConfirmDialog({
  title,
  detail,
  confirmLabel = "Confirm",
  danger,
  onCancel,
  onConfirm,
  busy,
}: {
  title: string;
  detail: string;
  confirmLabel?: string;
  danger?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  busy?: boolean;
}) {
  return (
    <div className="palette-backdrop" onClick={onCancel} role="presentation">
      <div className="palette" role="dialog" aria-labelledby="confirm-title" onClick={(e) => e.stopPropagation()}>
        <div style={{ padding: "1.1rem 1.15rem" }}>
          <h2 id="confirm-title">{title}</h2>
          <p>{detail}</p>
          <div className="row">
            <button type="button" className={danger ? "danger" : ""} onClick={onConfirm} disabled={busy}>
              {confirmLabel}
            </button>
            <button type="button" className="secondary" onClick={onCancel}>
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function EngineBanner({ engine }: { engine?: string }) {
  if (!engine || engine === "autodock-vina") return null;
  return (
    <div className="engine-banner" role="status">
      Docking engine is <strong className="mono">{engine}</strong> — AutoDock Vina is not available on the worker.
      Scores are prioritization heuristics, not binding energies.
    </div>
  );
}

export function DropZone({
  onFile,
  children,
}: {
  onFile: (file: File) => void;
  children: ReactNode;
}) {
  const [hot, setHot] = useState(false);
  return (
    <div
      className={cx("dropzone", hot && "hot")}
      onDragOver={(e) => {
        e.preventDefault();
        setHot(true);
      }}
      onDragLeave={() => setHot(false)}
      onDrop={(e) => {
        e.preventDefault();
        setHot(false);
        const file = e.dataTransfer.files?.[0];
        if (file) onFile(file);
      }}
    >
      {children}
    </div>
  );
}

type ToastKind = "ok" | "warn" | "danger";
type Toast = { id: number; kind: ToastKind; title: string; detail?: string };

const ToastCtx = createContext<{ push: (t: Omit<Toast, "id">) => void } | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { ...t, id }]);
    window.setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 4200);
  }, []);
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={cx("toast", t.kind)}>
            <strong>{t.title}</strong>
            {t.detail && <div className="muted">{t.detail}</div>}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastCtx);
  return ctx ?? { push: () => undefined };
}

const THEME_KEY = "opengero_theme";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "light" ? "light" : "dark";
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#070b0a" : "#eef4f1");
  }, [theme]);
  const value = useMemo(
    () => ({
      theme,
      toggle: () => setTheme((t) => (t === "dark" ? "light" : "dark")),
    }),
    [theme],
  );
  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}

const ThemeCtx = createContext<{ theme: "dark" | "light"; toggle: () => void }>({
  theme: "dark",
  toggle: () => undefined,
});

export function useTheme() {
  return useContext(ThemeCtx);
}

export function useBootSplash(ms = 900) {
  const [booting, setBooting] = useState(true);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) {
      setBooting(false);
      return;
    }
    const t = window.setTimeout(() => setBooting(false), ms);
    return () => window.clearTimeout(t);
  }, [ms]);
  return booting;
}
