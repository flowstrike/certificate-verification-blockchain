import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { saveSession } from "../lib/auth";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const session = await api.login(email, password);
      saveSession(session);
      navigate(session.role === "admin" ? "/admin" : "/issuer");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Login</h2>
      <p className="muted">
        Admin and Issuer login (email + password). Students do not log in:
        open a certificate with its Certificate ID or QR code on the
        Student page. Verifiers need no login.
      </p>
      <p className="muted">
        Local demo Admin: admin@demo.local / admin123 (change via
        ADMIN_EMAIL / ADMIN_PASSWORD on the backend — see README).
      </p>
      {error && <div className="error">{error}</div>}
      <form onSubmit={submit}>
        <label>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button disabled={busy}>{busy ? "Logging in…" : "Login"}</button>
      </form>
    </div>
  );
}
