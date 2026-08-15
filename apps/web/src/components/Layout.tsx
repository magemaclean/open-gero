import { useEffect, useMemo, useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, setToken } from "../api";
import type { Project, User } from "../types";
import {
  IconAdmin,
  IconChevron,
  IconDraw,
  IconFlask,
  IconJobs,
  IconLibrary,
  IconLogo,
  IconLogout,
  IconMoon,
  IconProjects,
  IconSearch,
  IconSun,
  IconTarget,
} from "./icons";
import { Breadcrumbs, EngineBanner, useTheme } from "./ui";
import { crumbsFor, lastProjectId, rememberProject } from "../lib/nav";

type NavItem = { to: string; label: string; icon: ReactNode; end?: boolean };

export function AppShell({ children, mode }: { children: ReactNode; mode: "projects" | "project" | "admin" }) {
  const { projectId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [engine, setEngine] = useState("");
  const [project, setProject] = useState<Project | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(() => lastProjectId());
  const { theme, toggle } = useTheme();

  useEffect(() => {
    api<User>("/api/auth/me")
      .then(setUser)
      .catch(() => setToken(null));
    api<{ docking_engine?: string }>("/api/meta")
      .then((m) => setEngine(m.docking_engine || ""))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    rememberProject(projectId);
    if (projectId) setResumeId(projectId);
    if (!projectId) {
      setProject(null);
      return;
    }
    api<Project>(`/api/projects/${projectId}`)
      .then(setProject)
      .catch(() => setProject(null));
  }, [projectId]);

  const projectItems = useMemo<NavItem[]>(() => {
    if (!projectId) return [];
    const base = `/projects/${projectId}`;
    return [
      { to: base, label: "Library", icon: <IconLibrary />, end: true },
      { to: `${base}/editor`, label: "Draw / add", icon: <IconDraw /> },
      { to: `${base}/search`, label: "Search", icon: <IconSearch /> },
      { to: `${base}/jobs`, label: "Jobs", icon: <IconJobs /> },
      { to: `${base}/datasets`, label: "Geroprotectors", icon: <IconFlask /> },
      { to: `${base}/targets`, label: "Targets", icon: <IconTarget /> },
    ];
  }, [projectId]);

  const crumbs = crumbsFor(location.pathname, project);
  const showResume = !projectId && resumeId;

  return (
    <div className={`shell${collapsed ? " collapsed" : ""}`}>
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          <span className="brand-mark">
            <IconLogo />
          </span>
          {!collapsed && (
            <span>
              OpenGero
              <small>{project?.name || (mode === "admin" ? "Administration" : "Projects")}</small>
            </span>
          )}
        </NavLink>
        <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} title="All projects">
          <IconProjects />
          {!collapsed && <span>All projects</span>}
        </NavLink>
        {showResume && (
          <NavLink to={`/projects/${resumeId}`} className="nav-link" title="Resume project">
            <IconChevron />
            {!collapsed && <span>Resume project</span>}
          </NavLink>
        )}
        {projectId && (
          <>
            {!collapsed && (
              <div className="nav-section">
                <div className="nav-section-label">This project</div>
                <div className="nav-section-name">{project?.name || "Loading…"}</div>
              </div>
            )}
            {projectItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
                title={item.label}
              >
                {item.icon}
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </>
        )}
        <div className="nav-spacer" />
        <NavLink to="/account" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} title="Account">
          <IconAdmin />
          {!collapsed && <span>Account</span>}
        </NavLink>
        {user?.role === "admin" && (
          <NavLink to="/admin" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} title="Admin">
            <IconAdmin />
            {!collapsed && <span>Admin</span>}
          </NavLink>
        )}
        <div className="sidebar-foot">
          {!collapsed && (
            <div className="user-chip">
              <div className="name">{user?.display_name || user?.email || "Signed in"}</div>
              <div className="muted" style={{ color: "#8aa398" }}>
                {user?.role || "researcher"} · <span className="kbd">⌘K</span>
              </div>
            </div>
          )}
          <div className="row" style={{ alignItems: "center" }}>
            <button className="icon-btn secondary" type="button" onClick={toggle} title="Toggle theme" aria-label="Toggle theme">
              {theme === "dark" ? <IconSun /> : <IconMoon />}
            </button>
            <button className="icon-btn secondary" type="button" onClick={() => setCollapsed((c) => !c)} title="Collapse sidebar" aria-label="Collapse sidebar">
              {collapsed ? "»" : "«"}
            </button>
            <button
              className="secondary"
              type="button"
              style={{ color: "#efe6d2", borderColor: "#3d4a44", flex: 1 }}
              onClick={() => {
                setToken(null);
                navigate("/login");
              }}
            >
              <IconLogout size={16} /> {!collapsed && "Sign out"}
            </button>
          </div>
        </div>
      </aside>
      <main className="main">
        <EngineBanner engine={engine} />
        <Breadcrumbs crumbs={crumbs} />
        {children}
      </main>
      <CommandPalette projectId={projectId} isAdmin={user?.role === "admin"} />
    </div>
  );
}

type Command = { id: string; label: string; hint: string; to: string };

function CommandPalette({ projectId, isAdmin }: { projectId?: string; isAdmin?: boolean }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);

  const commands = useMemo<Command[]>(() => {
    const list: Command[] = [
      { id: "home", label: "All projects", hint: "Home", to: "/" },
      { id: "account", label: "Account", hint: "Password", to: "/account" },
    ];
    if (isAdmin) list.push({ id: "admin", label: "Admin", hint: "Queue & users", to: "/admin" });
    if (projectId) {
      const base = `/projects/${projectId}`;
      list.push(
        { id: "lib", label: "Library", hint: "Molecules", to: base },
        { id: "draw", label: "Draw / add", hint: "Editor", to: `${base}/editor` },
        { id: "search", label: "Search", hint: "Similarity", to: `${base}/search` },
        { id: "jobs", label: "Jobs", hint: "Docking", to: `${base}/jobs` },
        { id: "data", label: "Geroprotectors", hint: "Dataset", to: `${base}/datasets` },
        { id: "targets", label: "Targets", hint: "Aging proteins", to: `${base}/targets` },
      );
    }
    return list;
  }, [projectId, isAdmin]);

  const filtered = commands.filter((c) => c.label.toLowerCase().includes(q.toLowerCase()) || c.hint.toLowerCase().includes(q.toLowerCase()));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
        setQ("");
        setIdx(0);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => setOpen(false), [location.pathname]);

  if (!open) return null;
  return (
    <div className="palette-backdrop" onClick={() => setOpen(false)}>
      <div className="palette" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Command palette">
        <input
          autoFocus
          placeholder="Jump to a workspace…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setIdx(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setIdx((i) => Math.min(filtered.length - 1, i + 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setIdx((i) => Math.max(0, i - 1));
            } else if (e.key === "Enter" && filtered[idx]) {
              navigate(filtered[idx].to);
              setOpen(false);
            }
          }}
        />
        {filtered.map((c, i) => (
          <button
            key={c.id}
            type="button"
            className={`palette-item${i === idx ? " active" : ""}`}
            onMouseEnter={() => setIdx(i)}
            onClick={() => {
              navigate(c.to);
              setOpen(false);
            }}
          >
            <span>{c.label}</span>
            <span className="muted">{c.hint}</span>
          </button>
        ))}
        {filtered.length === 0 && <div className="muted" style={{ padding: "0.9rem 1.1rem" }}>No matching destinations</div>}
      </div>
    </div>
  );
}
