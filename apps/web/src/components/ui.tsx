import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent, ReactNode } from "react";

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

export function Gauge({ label, value, max, unit }: { label: string; value: number; max: number; unit?: string }) {
  const p = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="gauge">
      <div className="ring" style={{ ["--p" as string]: p }} />
      <div>
        <div className="muted">{label}</div>
        <strong className="mono">
          {Number.isFinite(value) ? value.toFixed(value < 10 ? 2 : 1) : "—"}
          {unit ? ` ${unit}` : ""}
        </strong>
      </div>
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

export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setReduced(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}

export function useBootSplash(ms = 720) {
  const reduced = usePrefersReducedMotion();
  const [booting, setBooting] = useState(!reduced);
  const started = useRef(false);
  useEffect(() => {
    if (started.current || reduced) return;
    started.current = true;
    const t = window.setTimeout(() => setBooting(false), ms);
    return () => window.clearTimeout(t);
  }, [ms, reduced]);
  return booting;
}
