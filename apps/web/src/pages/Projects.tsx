import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { SkeletonCards } from "../components/Loading";
import { EmptyState, PageHeader, spotlightMove, useToast } from "../components/ui";
import type { Project } from "../types";

export function ProjectsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  async function load() {
    setProjects(await api<Project[]>("/api/projects"));
  }
  useEffect(() => {
    load()
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const p = await api<Project>("/api/projects", {
        method: "POST",
        body: JSON.stringify({ name, description }),
      });
      toast.push({ kind: "ok", title: "Project created", detail: p.name });
      navigate(`/projects/${p.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create project");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <PageHeader
        kicker="Workspace"
        title="Projects"
        subtitle="Group molecules, aging-related targets, and docking jobs. Soft-deleted projects are retained for 30 days."
      />
      {error && <div className="error" style={{ marginBottom: 12 }}>{error}</div>}
      <div className="grid grid-2">
        <form className="card" onSubmit={create}>
          <h2>New project</h2>
          <div className="grid">
            <div>
              <label>Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Senolytic shortlist" />
            </div>
            <div>
              <label>Description</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} placeholder="What are you screening?" />
            </div>
            <button type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create project"}
            </button>
          </div>
        </form>
        <div>
          {loading ? (
            <SkeletonCards count={2} />
          ) : projects.length === 0 ? (
            <EmptyState title="No projects yet" detail="Create one to start importing candidates and queuing docking jobs." />
          ) : (
            <div className="grid stagger">
              {projects.map((p) => (
                <Link
                  key={p.id}
                  to={`/projects/${p.id}`}
                  className="card interactive linkish"
                  onMouseMove={spotlightMove}
                >
                  <h3>{p.name}</h3>
                  <p>{p.description || "No description"}</p>
                  <span className="badge">{p.molecule_count} molecules</span>{" "}
                  <span className="badge">{p.job_count} jobs</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
