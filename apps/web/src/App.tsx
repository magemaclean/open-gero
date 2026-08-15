import { Navigate, NavLink, Outlet, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";
import type { User } from "./types";
import { LoginPage, RegisterPage } from "./pages/Auth";
import { ProjectsPage } from "./pages/Projects";
import { LibraryPage } from "./pages/Library";
import { EditorPage } from "./pages/Editor";
import { MoleculePage } from "./pages/Molecule";
import { SearchPage } from "./pages/Search";
import { JobsPage, JobDetailPage } from "./pages/Jobs";
import { DatasetsPage } from "./pages/Datasets";
import { TargetsPage } from "./pages/Targets";
import { AdminPage } from "./pages/Admin";

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectLayout />}>
            <Route index element={<LibraryPage />} />
            <Route path="editor" element={<EditorPage />} />
            <Route path="molecules/:moleculeId" element={<MoleculePage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="jobs" element={<JobsPage />} />
            <Route path="jobs/:jobId" element={<JobDetailPage />} />
            <Route path="datasets" element={<DatasetsPage />} />
            <Route path="targets" element={<TargetsPage />} />
          </Route>
          <Route path="/admin" element={<AdminPage />} />
        </Route>
      </Routes>
      <div className="disclaimer" role="note">
        Research tool only — not medical advice. Docking scores and similarity ranks are computational
        prioritization heuristics, not experimental measurements or dosing guidance.
      </div>
    </>
  );
}

function RequireAuth() {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function ProjectLayout() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    api<User>("/api/auth/me").then(setUser).catch(() => setToken(null));
  }, []);
  const link = (to: string, label: string) => (
    <NavLink to={to} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} end={to.endsWith(projectId || "")}>
      {label}
    </NavLink>
  );
  return (
    <div className="shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          OpenGero
          <small>Longevity screening</small>
        </NavLink>
        {link(`/projects/${projectId}`, "Library")}
        {link(`/projects/${projectId}/editor`, "Draw / add")}
        {link(`/projects/${projectId}/search`, "Search")}
        {link(`/projects/${projectId}/jobs`, "Jobs")}
        {link(`/projects/${projectId}/datasets`, "Geroprotectors")}
        {link(`/projects/${projectId}/targets`, "Targets")}
        {user?.role === "admin" && (
          <NavLink to="/admin" className="nav-link">
            Admin
          </NavLink>
        )}
        <div style={{ marginTop: "auto", paddingTop: "1rem" }}>
          <div className="muted" style={{ color: "#b7aa90" }}>
            {user?.display_name || user?.email}
          </div>
          <button
            className="secondary"
            style={{ marginTop: 8, color: "#efe6d2", borderColor: "#5a4f3d" }}
            onClick={() => {
              setToken(null);
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
