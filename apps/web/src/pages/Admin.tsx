import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { User } from "../types";

type Stats = {
  users: number;
  projects: number;
  molecules: number;
  jobs_queued: number;
  jobs_running: number;
  jobs_failed: number;
  disk_bytes: number;
  dataset_version: string;
};

export function AdminPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [jobs, setJobs] = useState<{ id: string; type: string; status: string; error: string }[]>([]);
  useEffect(() => {
    api<Stats>("/api/admin/stats").then(setStats);
    api<User[]>("/api/admin/users").then(setUsers);
    api<typeof jobs>("/api/admin/jobs").then(setJobs);
  }, []);
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link to="/" className="brand">
          OpenGero
          <small>Admin</small>
        </Link>
        <Link className="nav-link" to="/">
          Projects
        </Link>
      </aside>
      <main className="main">
        <h1>Administration</h1>
        {stats && (
          <div className="grid grid-3">
            <Stat label="Users" value={stats.users} />
            <Stat label="Projects" value={stats.projects} />
            <Stat label="Molecules" value={stats.molecules} />
            <Stat label="Queued jobs" value={stats.jobs_queued} />
            <Stat label="Running" value={stats.jobs_running} />
            <Stat label="Failed" value={stats.jobs_failed} />
            <Stat label="Disk (bytes)" value={stats.disk_bytes} />
            <Stat label="Dataset" value={stats.dataset_version} />
          </div>
        )}
        <h2>Users</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h2>Queue health</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Status</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td>{j.type}</td>
                  <td>{j.status}</td>
                  <td>{j.error}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <div className="muted">{label}</div>
      <div className="serif" style={{ fontSize: "1.6rem" }}>
        {value}
      </div>
    </div>
  );
}
