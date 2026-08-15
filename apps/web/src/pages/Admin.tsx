import { useEffect, useState } from "react";
import { api } from "../api";
import { SkeletonCards, SkeletonTable } from "../components/Loading";
import { ConfirmDialog, ActionMenu, PageHeader, StatCard, useToast } from "../components/ui";
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
  docking_engine?: string;
  vina_available?: boolean;
};

export function AdminPage() {
  const toast = useToast();
  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [me, setMe] = useState<User | null>(null);
  const [jobs, setJobs] = useState<{ id: string; type: string; status: string; error: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingDisable, setPendingDisable] = useState<User | null>(null);

  async function load() {
    const [s, u, j, self] = await Promise.all([
      api<Stats>("/api/admin/stats"),
      api<User[]>("/api/admin/users?include_disabled=true"),
      api<typeof jobs>("/api/admin/jobs"),
      api<User>("/api/auth/me"),
    ]);
    setStats(s);
    setUsers(u);
    setJobs(j);
    setMe(self);
  }
  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  async function setRole(user: User, role: string) {
    await api(`/api/admin/users/${user.id}/role?role=${role}`, { method: "POST" });
    toast.push({ kind: "ok", title: "Role updated", detail: `${user.email} → ${role}` });
    await load();
  }

  return (
    <div>
      <PageHeader
        kicker="Operations"
        title="Administration"
        subtitle="Users, disk usage, and queue health for this instance. Disable the seeded demo admin before a shared lab deploy."
      />
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
          <StatCard label="Docking engine" value={stats.docking_engine || "unknown"} />
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
                <th>Status</th>
                <th className="row-actions" />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    {u.email}
                    {u.email === "demo@opengero.local" && <div className="badge warn">demo</div>}
                  </td>
                  <td>{u.display_name}</td>
                  <td>
                    <select
                      value={u.role}
                      disabled={!!u.deleted_at}
                      onChange={(e) => setRole(u, e.target.value)}
                    >
                      <option value="admin">admin</option>
                      <option value="user">user</option>
                    </select>
                  </td>
                  <td>
                    <span className={`badge ${u.deleted_at ? "danger" : "ok"}`}>{u.deleted_at ? "disabled" : "active"}</span>
                  </td>
                  <td className="row-actions">
                    <ActionMenu
                      items={
                        u.deleted_at
                          ? [
                              {
                                label: "Enable",
                                onClick: () => api(`/api/admin/users/${u.id}/enable`, { method: "POST" }).then(() => load()),
                              },
                            ]
                          : [{ label: "Disable", danger: true, disabled: u.id === me?.id, onClick: () => setPendingDisable(u) }]
                      }
                    />
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
      {pendingDisable && (
        <ConfirmDialog
          title={`Disable ${pendingDisable.email}?`}
          detail={
            pendingDisable.email === "demo@opengero.local"
              ? "This is the seeded demo admin. They will not be able to sign in until re-enabled."
              : "The account is soft-deleted and cannot sign in until re-enabled."
          }
          confirmLabel="Disable account"
          danger
          onCancel={() => setPendingDisable(null)}
          onConfirm={async () => {
            await api(`/api/admin/users/${pendingDisable.id}/disable`, { method: "POST" });
            toast.push({ kind: "ok", title: "User disabled" });
            setPendingDisable(null);
            await load();
          }}
        />
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
