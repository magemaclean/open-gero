import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { PageHeader, useToast } from "../components/ui";
import type { AssistantStatus } from "../types";

export function AccountPage() {
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [assistant, setAssistant] = useState<AssistantStatus | null>(null);
  const [provider, setProvider] = useState("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [assistError, setAssistError] = useState("");
  const [assistBusy, setAssistBusy] = useState(false);

  useEffect(() => {
    api<AssistantStatus>("/api/assistant/status")
      .then((s) => {
        setAssistant(s);
        if (s.provider) setProvider(s.provider);
      })
      .catch(() => undefined);
  }, []);

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

  async function saveKey(e: FormEvent) {
    e.preventDefault();
    setAssistError("");
    setAssistBusy(true);
    try {
      const s = await api<AssistantStatus>("/api/assistant/settings", {
        method: "PUT",
        body: JSON.stringify({ provider, api_key: apiKey }),
      });
      setAssistant(s);
      setApiKey("");
      toast.push({ kind: "ok", title: "Assistant key saved" });
    } catch (err) {
      setAssistError(err instanceof Error ? err.message : "Could not save key");
    } finally {
      setAssistBusy(false);
    }
  }

  async function clearKey() {
    setAssistBusy(true);
    try {
      const s = await api<AssistantStatus>("/api/assistant/settings", {
        method: "PUT",
        body: JSON.stringify({ clear: true }),
      });
      setAssistant(s);
      toast.push({ kind: "ok", title: "Assistant key removed" });
    } catch (err) {
      setAssistError(err instanceof Error ? err.message : "Could not clear key");
    } finally {
      setAssistBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        kicker="Account"
        title="Account"
        subtitle="Password for this signed-in user, plus an optional assistant API key. Lab-wide keys can also be set as ASSISTANT_API_KEY on the API. Disable the seeded demo admin from Admin before sharing a lab instance."
      />
      <form className="card" onSubmit={onSubmit} style={{ maxWidth: 440 }}>
        <h2>Password</h2>
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
      <form className="card" onSubmit={saveKey} style={{ maxWidth: 440, marginTop: 16 }}>
        <h2>Workbench assistant</h2>
        <p className="muted">
          Anthropic or OpenAI API key for the in-app assistant. The key is stored encrypted and never shown again.
          Prompts leave this host to that provider. Research tool only — not medical advice.
        </p>
        <p className="muted">
          {assistant?.configured
            ? `Configured via ${assistant.source} key (${assistant.provider}, ${assistant.model}).`
            : "Not configured. Add a user key here or a lab key on the API container."}
        </p>
        <div>
          <label>Provider</label>
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
          </select>
        </div>
        <div style={{ marginTop: 10 }}>
          <label>API key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            autoComplete="off"
            placeholder={assistant?.has_user_key ? "Saved — paste a new key to replace" : "sk-… or sk-ant-…"}
            required={!assistant?.has_user_key}
          />
        </div>
        {assistError && <div className="error" style={{ marginTop: 10 }}>{assistError}</div>}
        <div className="row" style={{ marginTop: 12 }}>
          <button type="submit" disabled={assistBusy}>
            {assistBusy ? "Saving…" : "Save key"}
          </button>
          {assistant?.has_user_key && (
            <button type="button" className="secondary" onClick={clearKey} disabled={assistBusy}>
              Remove key
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
