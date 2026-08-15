import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { getToken } from "./api";
import { AppShell } from "./components/Layout";
import { BootScreen } from "./components/Loading";
import { ThemeProvider, ToastProvider, useBootSplash } from "./components/ui";
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
    <ThemeProvider>
      <ToastProvider>
        <AppRoutes />
      </ToastProvider>
    </ThemeProvider>
  );
}

function AppRoutes() {
  const booting = useBootSplash();
  return (
    <>
      {booting && <BootScreen />}
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<RequireAuth />}>
          <Route
            path="/"
            element={
              <AppShell mode="projects">
                <ProjectsPage />
              </AppShell>
            }
          />
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
          <Route
            path="/admin"
            element={
              <AppShell mode="admin">
                <AdminPage />
              </AppShell>
            }
          />
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
  return (
    <AppShell mode="project">
      <Outlet />
    </AppShell>
  );
}
