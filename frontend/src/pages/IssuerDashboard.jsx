import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { getSession } from "../lib/auth";

// Issuer Dashboard design, notes Section 14: total / active / revoked
// counts, Register Certificate action, Recent Certificates, and
// Dashboard / Register / Certificates / Revoke / Logout navigation.
export default function IssuerDashboard() {
  const session = getSession();
  const [certs, setCerts] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (session?.issuer_id) {
      api
        .listIssuerCertificates(session.issuer_id)
        .then(setCerts)
        .catch((err) => setError(err.message));
    }
  }, []);

  if (session?.role !== "issuer") {
    return (
      <div className="card">
        <p>Issuer login required. <Link to="/login">Login</Link></p>
      </div>
    );
  }

  const total = certs.length;
  const active = certs.filter((c) => c.blockchain_status === "ACTIVE").length;
  const revoked = certs.filter((c) => c.blockchain_status === "REVOKED").length;
  const pending = total - active - revoked;

  return (
    <div className="sidebar">
      <nav>
        <Link to="/issuer">Dashboard</Link>
        <Link to="/register">Register Certificate</Link>
        <Link to="/issuer/certificates">Certificates</Link>
        <Link to="/revoke">Revoke</Link>
        <Link to="/transactions">Transaction Status</Link>
        <Link to="/history">Verification History</Link>
      </nav>
      <div style={{ flex: 1 }}>
        <h2>Issuer Dashboard</h2>
        <p className="muted">
          {session.college_name} — {session.wallet_address} — Status:{" "}
          {session.authorization_status}
        </p>
        {session.authorization_status !== "AUTHORIZED" && (
          <div className="error">
            Your issuer account is PENDING. An Admin must authorize it
            before you can register certificates.
          </div>
        )}
        {error && <div className="error">{error}</div>}
        <div className="card">
          <p>Total Certificates: {total}</p>
          <p>Active: {active}</p>
          <p>Revoked: {revoked}</p>
          {pending > 0 && (
            <p className="muted">Not yet registered on-chain: {pending}</p>
          )}
          <Link to="/register">
            <button disabled={session.authorization_status !== "AUTHORIZED"}>
              Register Certificate
            </button>
          </Link>
        </div>
        <div className="card">
          <h3>Recent Certificates</h3>
          {certs.slice(-5).reverse().map((c) => (
            <p key={c.certificate_id}>
              {c.certificate_id} — {c.student_name} — {c.course} —{" "}
              {c.blockchain_status}
            </p>
          ))}
          {certs.length === 0 && <p className="muted">No certificates yet.</p>}
        </div>
      </div>
    </div>
  );
}
