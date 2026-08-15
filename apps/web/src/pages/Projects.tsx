import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { SkeletonCards } from "../components/Loading";
import { ConfirmDialog, EmptyState, PageHeader, spotlightMove, useToast } from "../components/ui";
import type { Project } from "../types";

export function ProjectsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [deleted, setDeleted] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Project | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const [live, gone] = await Promise.all([
      api<Project[]>("/api/projects"),
      api<Project[]>("/api/projects?deleted=true"),
    ]);
    setProjects(live);
    setDeleted(gone);
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

  async function saveEdit(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setBusy(true);
    try {
      await api(`/api/projects/${editing.id}`, {
        method: "PATCH",
        body: JSON.stringify({ name: editName, description: editDescription }),
      });
      toast.push({ kind: "ok", title: "Project updated" });
      setEditing(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update");
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setBusy(true);
    try {
      await api(`/api/projects/${pendingDelete.id}?confirm=true`, { method: "DELETE" });
      toast.push({ kind: "ok", title: "Project deleted", detail: "Retained for 30 days" });
      setPendingDelete(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete");
    } finally {
      setBusy(false);
    }
  }

  async function restore(p: Project) {
    await api(`/api/projects/${p.id}/restore`, { method: "POST" });
    toast.push({ kind: "ok", title: "Project restored", detail: p.name });
    await load();
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
                <div key={p.id} className="card interactive" onMouseMove={spotlightMove}>
                  <Link to={`/projects/${p.id}`} className="linkish" style={{ textDecoration: "none", color: "inherit" }}>
                    <h3>{p.name}</h3>
                    <p>{p.description || "No description"}</p>
                  </Link>
                  <span className="badge">{p.molecule_count} molecules</span>{" "}
                  <span className="badge">{p.job_count} jobs</span>
                  <div className="row" style={{ marginTop: 10 }}>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => {
                        setEditing(p);
                        setEditName(p.name);
                        setEditDescription(p.description);
                      }}
                    >
                      Edit
                    </button>
                    <button type="button" className="danger" onClick={() => setPendingDelete(p)}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {deleted.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h2>Recently deleted</h2>
          <p className="muted">Restorable for 30 days.</p>
          <div className="grid">
            {deleted.map((p) => (
              <div key={p.id} className="card">
                <strong>{p.name}</strong>
                <p style={{ marginBottom: 8 }}>{p.description || "No description"}</p>
                <button type="button" className="secondary" onClick={() => restore(p)}>
                  Restore
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
      {editing && (
        <div className="palette-backdrop" onClick={() => setEditing(null)}>
          <div className="palette" onClick={(e) => e.stopPropagation()}>
            <form onSubmit={saveEdit} style={{ padding: "1.1rem" }}>
              <h2>Edit project</h2>
              <label>Name</label>
              <input value={editName} onChange={(e) => setEditName(e.target.value)} required />
              <label style={{ marginTop: 8 }}>Description</label>
              <textarea value={editDescription} onChange={(e) => setEditDescription(e.target.value)} rows={3} />
              <div className="row" style={{ marginTop: 12 }}>
                <button type="submit" disabled={busy}>
                  Save
                </button>
                <button type="button" className="secondary" onClick={() => setEditing(null)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {pendingDelete && (
        <ConfirmDialog
          title={`Delete ${pendingDelete.name}?`}
          detail="The project is soft-deleted and retained for 30 days. You can restore it from this page."
          confirmLabel="Delete project"
          danger
          busy={busy}
          onCancel={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
        />
      )}
    </div>
  );
}
