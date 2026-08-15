import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, setToken } from "../api";
import type { Project, User } from "../types";

export function ProjectsPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");

  async function load() {
    setProjects(await api<Project[]>("/api/projects"));
  }
  useEffect(() => {
    api<User>("/api/auth/me").then(setUser);
    load().catch((e) => setError(String(e)));
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    const p = await api<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
    navigate(`/projects/${p.id}`);
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          OpenGero
          <small>Projects</small>
        </div>
        {user?.role === "admin" && (
          <Link className="nav-link" to="/admin">
            Admin
          </Link>
        )}
        <button
          className="secondary"
          style={{ marginTop: "auto", color: "#efe6d2", borderColor: "#5a4f3d" }}
          onClick={() => {
            setToken(null);
            navigate("/login");
          }}
        >
          Sign out
        </button>
      </aside>
      <main className="main">
        <h1>Projects</h1>
        <p>Group molecules, aging-related targets, and docking jobs. Soft-deleted projects are retained for 30 days.</p>
        {error && <div className="error">{error}</div>}
        <div className="grid grid-2">
          <div className="card">
            <h2>New project</h2>
            <form onSubmit={create} className="grid">
              <div>
                <label>Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div>
                <label>Description</label>
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
              </div>
              <button type="submit">Create project</button>
            </form>
          </div>
          <div className="grid">
            {projects.map((p) => (
              <Link key={p.id} to={`/projects/${p.id}`} className="card" style={{ textDecoration: "none", color: "inherit" }}>
                <h3>{p.name}</h3>
                <p>{p.description || "No description"}</p>
                <span className="badge">{p.molecule_count} molecules</span>{" "}
                <span className="badge">{p.job_count} jobs</span>
              </Link>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
