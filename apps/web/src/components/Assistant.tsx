import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, getToken } from "../api";
import type { AssistantStatus } from "../types";
import { IconClose, IconSpark } from "./icons";
import { useToast } from "./ui";

type PendingAction = { name: string; summary: string; arguments: Record<string, unknown> };
type ChatTurn = {
  role: "user" | "assistant";
  content: string;
  pending?: PendingAction[];
  confirmId?: string | null;
  downloads?: { filename: string; url: string }[];
};

type ChatResponse = {
  reply: string;
  pending_actions: PendingAction[];
  confirm_id: string | null;
  downloads: { filename: string; url: string }[];
};

export function AssistantHost() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onOpen = () => setOpen(true);
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === "j") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("opengero:assistant", onOpen);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("opengero:assistant", onOpen);
      window.removeEventListener("keydown", onKey);
    };
  }, []);
  return (
    <>
      <button
        type="button"
        className="assistant-fab"
        onClick={() => setOpen(true)}
        title="Workbench assistant (Ctrl+Shift+J)"
        aria-label="Open workbench assistant"
      >
        <IconSpark size={18} />
      </button>
      {open && <AssistantPanel onClose={() => setOpen(false)} />}
    </>
  );
}

function AssistantPanel({ onClose }: { onClose: () => void }) {
  const { projectId } = useParams();
  const toast = useToast();
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<AssistantStatus>("/api/assistant/status")
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  async function send(e?: FormEvent) {
    e?.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    setError("");
    const nextTurns: ChatTurn[] = [...turns, { role: "user", content: text }];
    setTurns(nextTurns);
    setBusy(true);
    try {
      const messages = nextTurns
        .filter((t) => t.role === "user" || (t.role === "assistant" && !t.pending?.length))
        .map((t) => ({ role: t.role, content: t.content }));
      const body = await api<ChatResponse>("/api/assistant/chat", {
        method: "POST",
        body: JSON.stringify({ messages, project_id: projectId || null }),
      });
      setTurns((prev) => [
        ...prev,
        {
          role: "assistant",
          content: body.reply,
          pending: body.pending_actions,
          confirmId: body.confirm_id,
          downloads: body.downloads,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assistant failed");
    } finally {
      setBusy(false);
    }
  }

  async function confirm(confirmId: string) {
    setBusy(true);
    setError("");
    try {
      const body = await api<ChatResponse>("/api/assistant/confirm", {
        method: "POST",
        body: JSON.stringify({ confirm_id: confirmId }),
      });
      setTurns((prev) => [
        ...prev.map((t) => (t.confirmId === confirmId ? { ...t, pending: [], confirmId: null } : t)),
        { role: "assistant", content: body.reply, downloads: body.downloads },
      ]);
      toast.push({ kind: "ok", title: "Assistant action ran" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm");
    } finally {
      setBusy(false);
    }
  }

  async function reject(confirmId: string) {
    try {
      await api("/api/assistant/reject", { method: "POST", body: JSON.stringify({ confirm_id: confirmId }) });
    } catch {
      /* expired is fine */
    }
    setTurns((prev) => prev.map((t) => (t.confirmId === confirmId ? { ...t, pending: [], confirmId: null, content: t.content + "\n\n(Cancelled.)" } : t)));
  }

  return (
    <aside className="assistant-panel" role="dialog" aria-label="Workbench assistant">
      <header className="assistant-head">
        <div>
          <strong>Assistant</strong>
          <div className="muted">
            {status?.configured
              ? `${status.provider} · ${status.source} key`
              : "No API key — add one on Account"}
          </div>
        </div>
        <button type="button" className="icon-btn secondary" onClick={onClose} aria-label="Close assistant">
          <IconClose size={16} />
        </button>
      </header>
      <div className="assistant-body" ref={scroller}>
        {turns.length === 0 && (
          <p className="muted">
            Ask about this project’s library, similarity, or jobs. Writes (import, dock, export, create project) wait for
            your confirm. Research tool only — not medical advice.
          </p>
        )}
        {turns.map((t, i) => (
          <div key={i} className={`assistant-msg ${t.role}`}>
            <div className="assistant-bubble">{t.content}</div>
            {t.pending && t.pending.length > 0 && t.confirmId && (
              <div className="assistant-confirm">
                <div className="muted">Confirm to run</div>
                <ul>
                  {t.pending.map((p, j) => (
                    <li key={j}>{p.summary}</li>
                  ))}
                </ul>
                <div className="row">
                  <button type="button" onClick={() => confirm(t.confirmId!)} disabled={busy}>
                    {busy ? "Running…" : "Confirm"}
                  </button>
                  <button type="button" className="secondary" onClick={() => reject(t.confirmId!)} disabled={busy}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
            {t.downloads?.map((d) => (
              <button key={d.url} type="button" className="secondary" onClick={() => pullDownload(d.url, d.filename)}>
                Download {d.filename}
              </button>
            ))}
          </div>
        ))}
        {busy && <div className="muted">Thinking…</div>}
        {error && <div className="error">{error}</div>}
      </div>
      <form className="assistant-compose" onSubmit={send}>
        <textarea
          rows={2}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={status?.configured ? "Ask or instruct…" : "Configure a key on Account first"}
          disabled={!status?.configured || busy}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
        />
        <button type="submit" disabled={!status?.configured || busy || !draft.trim()}>
          Send
        </button>
      </form>
    </aside>
  );
}

async function pullDownload(path: string, filename: string) {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const resp = await fetch(path, { headers });
  if (!resp.ok) throw new Error("Download expired");
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
