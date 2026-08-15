import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, setToken } from "../api";
import { IconLogo } from "../components/icons";
import { ButtonSpinner } from "../components/Loading";
import { useTheme } from "../components/ui";
import { IconMoon, IconSun } from "../components/icons";

export function LoginPage() {
  return <AuthForm mode="login" />;
}

export function RegisterPage() {
  return <AuthForm mode="register" />;
}

function AuthForm({ mode }: { mode: "login" | "register" }) {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const [email, setEmail] = useState(mode === "login" ? "demo@opengero.local" : "");
  const [password, setPassword] = useState(mode === "login" ? "demo12345" : "");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const body =
        mode === "login" ? { email, password } : { email, password, display_name: name };
      const resp = await api<{ access_token: string }>(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setToken(resp.access_token);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-hero">
        <div className="field" aria-hidden="true">
          <div className="hex-grid" />
          <div className="orb a" />
          <div className="orb b" />
          <div className="orb c" />
        </div>
        <div style={{ position: "relative", zIndex: 1 }}>
          <div className="brand" style={{ margin: "0 0 1.2rem" }}>
            <span className="brand-mark">
              <IconLogo />
            </span>
            <span>
              OpenGero
              <small>Longevity screening</small>
            </span>
          </div>
          <h1>Screen candidates before the wet lab.</h1>
          <p style={{ maxWidth: 440, color: "#c5d6ce" }}>
            Import structures, score drug-likeness, search curated geroprotectors, and dock against aging-related
            targets — with full provenance from one workbench.
          </p>
        </div>
      </section>
      <section className="auth-panel">
        <div className="card auth-card interactive" style={{ padding: "1.4rem 1.35rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
            <div>
              <div className="page-kicker">{mode === "login" ? "Welcome back" : "Create workspace"}</div>
              <div className="serif" style={{ fontSize: "1.7rem" }}>
                {mode === "login" ? "Sign in" : "Register"}
              </div>
            </div>
            <button className="icon-btn secondary" type="button" onClick={toggle} aria-label="Toggle theme">
              {theme === "dark" ? <IconSun /> : <IconMoon />}
            </button>
          </div>
          <p>Self-hosted in-silico screening for geroscience labs.</p>
          <form onSubmit={onSubmit} className="grid" style={{ gap: "0.8rem" }}>
            {mode === "register" && (
              <div>
                <label>Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
              </div>
            )}
            <div>
              <label>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
            </div>
            <div>
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            </div>
            {error && <div className="error">{error}</div>}
            <button type="submit" disabled={busy}>
              {busy && <ButtonSpinner />}
              {mode === "login" ? "Enter workbench" : "Create account"}
            </button>
          </form>
          <p className="muted" style={{ marginTop: "1rem", marginBottom: 0 }}>
            {mode === "login" ? (
              <>
                No account? <Link to="/register">Register</Link>. Demo: <span className="mono">demo@opengero.local</span> /{" "}
                <span className="mono">demo12345</span>
              </>
            ) : (
              <Link to="/login">Back to sign in</Link>
            )}
          </p>
        </div>
      </section>
    </div>
  );
}
