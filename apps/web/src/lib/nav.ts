export const LAST_PROJECT_KEY = "opengero_last_project";

export type Crumb = { label: string; to?: string };

export function rememberProject(projectId: string | undefined) {
  if (!projectId || typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(LAST_PROJECT_KEY, projectId);
}

export function lastProjectId(): string | null {
  if (typeof sessionStorage === "undefined") return null;
  return sessionStorage.getItem(LAST_PROJECT_KEY);
}

/** Extra breadcrumb after Projects / {project name}. Null on the project library home. */
export function projectPageLabel(pathname: string, projectId?: string): string | null {
  if (!projectId) return null;
  const prefix = `/projects/${projectId}`;
  if (!pathname.startsWith(prefix)) return null;
  const rest = pathname.slice(prefix.length) || "/";
  if (rest === "/") return null;
  if (rest.startsWith("/editor")) return "Draw / add";
  if (rest.startsWith("/search")) return "Search";
  if (rest.startsWith("/jobs/") && rest !== "/jobs") return "Job";
  if (rest.startsWith("/jobs")) return "Jobs";
  if (rest.startsWith("/datasets")) return "Geroprotectors";
  if (rest.startsWith("/targets")) return "Targets";
  if (rest.startsWith("/molecules/")) return "Molecule";
  return null;
}

export function crumbsFor(pathname: string, project?: { id: string; name: string } | null): Crumb[] {
  const crumbs: Crumb[] = [{ label: "Projects", to: "/" }];
  if (pathname === "/account") {
    crumbs.push({ label: "Account" });
    return crumbs;
  }
  if (pathname === "/admin") {
    crumbs.push({ label: "Admin" });
    return crumbs;
  }
  if (!project) return crumbs;
  const page = projectPageLabel(pathname, project.id);
  crumbs.push({ label: project.name, to: page ? `/projects/${project.id}` : undefined });
  if (page) crumbs.push({ label: page });
  return crumbs;
}
