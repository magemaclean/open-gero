import { FormEvent, useState } from "react";
import { api } from "../api";
import { PageHeader, useToast } from "../components/ui";

export function AccountPage() {
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api("/api/auth/password", {
        method: "POST",
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      toast.push({ kind: "ok", title: "Password updated" });
      setCurrent("");
      setNext("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change password");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        kicker="Account"
        title="Password"
        subtitle="Change the password for this signed-in account. Disable the seeded demo admin from Admin before sharing a lab instance."
      />
      <form className="card" onSubmit={onSubmit} style={{ maxWidth: 440 }}>
        <div>
          <label>Current password</label>
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required autoComplete="current-password" />
        </div>
        <div style={{ marginTop: 10 }}>
          <label>New password</label>
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} required minLength={8} autoComplete="new-password" />
        </div>
        {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
        <button type="submit" style={{ marginTop: 12 }} disabled={busy}>
          {busy ? "Saving…" : "Update password"}
        </button>
      </form>
    </div>
  );
}
