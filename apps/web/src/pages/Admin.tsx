import { useEffect, useState } from "react";
import { api } from "../api";
import { SkeletonCards, SkeletonTable } from "../components/Loading";
import { PageHeader, StatCard } from "../components/ui";
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
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([api<Stats>("/api/admin/stats"), api<User[]>("/api/admin/users"), api<typeof jobs>("/api/admin/jobs")])
      .then(([s, u, j]) => {
        setStats(s);
        setUsers(u);
        setJobs(j);
      })
      .finally(() => setLoading(false));
  }, []);
  return (
    <div>
      <PageHeader kicker="Operations" title="Administration" subtitle="Users, disk usage, and queue health for this instance." />
      {loading || !stats ? (
        <SkeletonCards count={4} />
      ) : (
        <div className="grid grid-3 stagger">
          <StatCard label="Users" value={stats.users} />
          <StatCard label="Projects" value={stats.projects} />
          <StatCard label="Molecules" value={stats.molecules} />
          <StatCard label="Queued jobs" value={stats.jobs_queued} />
          <StatCard label="Running" value={stats.jobs_running} />
          <StatCard label="Failed" value={stats.jobs_failed} />
          <StatCard label="Disk" value={formatBytes(stats.disk_bytes)} hint="Persistent storage" />
          <StatCard label="Dataset" value={stats.dataset_version} />
        </div>
      )}
      <h2 style={{ marginTop: 24 }}>Users</h2>
      {loading ? (
        <SkeletonTable rows={3} />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Email</th>
                <th>Name</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.display_name}</td>
                  <td>
                    <span className={`badge ${u.role === "admin" ? "ok" : ""}`}>{u.role}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <h2 style={{ marginTop: 24 }}>Queue health</h2>
      {loading ? (
        <SkeletonTable rows={3} />
      ) : (
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
                  <td>
                    <span className={`badge ${j.status === "done" ? "ok" : j.status === "failed" ? "danger" : "warn"}`}>
                      {j.status}
                    </span>
                  </td>
                  <td>{j.error}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}
