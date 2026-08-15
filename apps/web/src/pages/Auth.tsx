import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, setToken } from "../api";

export function LoginPage() {
  return <AuthForm mode="login" />;
}

export function RegisterPage() {
  return <AuthForm mode="register" />;
}

function AuthForm({ mode }: { mode: "login" | "register" }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState(mode === "login" ? "demo@opengero.local" : "");
  const [password, setPassword] = useState(mode === "login" ? "demo12345" : "");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
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
    }
  }
  return (
    <div className="auth-page">
      <div className="card auth-card">
        <div className="serif" style={{ fontSize: "1.8rem" }}>
          OpenGero
        </div>
        <p>Self-hosted in-silico screening for geroscience labs.</p>
        <form onSubmit={onSubmit} className="grid" style={{ gap: "0.75rem" }}>
          {mode === "register" && (
            <div>
              <label>Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
          )}
          <div>
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
          </div>
          {error && <div className="error">{error}</div>}
          <button type="submit">{mode === "login" ? "Sign in" : "Create account"}</button>
        </form>
        <p className="muted" style={{ marginTop: "1rem" }}>
          {mode === "login" ? (
            <>
              No account? <Link to="/register">Register</Link>. Demo: demo@opengero.local / demo12345
            </>
          ) : (
            <Link to="/login">Back to sign in</Link>
          )}
        </p>
      </div>
    </div>
  );
}
