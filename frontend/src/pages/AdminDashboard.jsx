import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { getSession } from "../lib/auth";

// Admin responsibilities, notes Section 4A: authorize a college/issuer,
// view authorized issuers, manage issuer access, prevent unauthorized
// users from issuing certificates.
export default function AdminDashboard() {
  const session = getSession();
  const [issuers, setIssuers] = useState([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    college_name: "",
    wallet_address: "",
    email: "",
    password: "",
  });

  async function load() {
    try {
      setIssuers(await api.listIssuers());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (session?.role !== "admin") {
    return (
      <div className="card">
        <p>Admin login required. <Link to="/login">Login</Link></p>
      </div>
    );
  }

  async function create(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await api.createIssuer(form);
      setMessage("Issuer created (PENDING). Authorize it below to allow issuing.");
      setForm({ college_name: "", wallet_address: "", email: "", password: "" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function authorize(id) {
    setError("");
    try {
      await api.authorizeIssuer(id);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <h2>Admin Dashboard</h2>
      <p className="muted">
        Note: authorizing here authorizes the issuer in the database.
        The wallet must also be authorized on-chain by the Admin's
        authorize transaction (Phase 3 submit script, or a future Admin
        wallet button) before on-chain registration will succeed.
      </p>
      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}

      <div className="card">
        <h3>Authorized Issuers</h3>
        {issuers.length === 0 ? (
          <p className="muted">No issuers yet.</p>
        ) : (
          <table>
            <thead>
              <tr><th>College</th><th>Wallet</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {issuers.map((issuer) => (
                <tr key={issuer.id}>
                  <td>{issuer.college_name}</td>
                  <td style={{ wordBreak: "break-all" }}>{issuer.wallet_address}</td>
                  <td>{issuer.authorization_status}</td>
                  <td>
                    {issuer.authorization_status !== "AUTHORIZED" && (
                      <button onClick={() => authorize(issuer.id)}>Authorize</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h3>Add Issuer</h3>
        <form onSubmit={create}>
          <label>College Name</label>
          <input value={form.college_name} onChange={(e) => setForm({ ...form, college_name: e.target.value })} required />
          <label>Wallet Address</label>
          <input value={form.wallet_address} onChange={(e) => setForm({ ...form, wallet_address: e.target.value })} required />
          <label>Email (for Issuer login)</label>
          <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <label>Password (for Issuer login)</label>
          <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <button>Add Issuer</button>
        </form>
      </div>
    </div>
  );
}
