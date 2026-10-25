import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { getSession } from "../lib/auth";

export default function TransactionStatus() {
  const session = getSession();
  const [status, setStatus] = useState(null);
  const [certs, setCerts] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getBlockchainStatus()
      .then(setStatus)
      .catch((err) => setError(err.message));
    if (session?.role === "issuer" && session.issuer_id) {
      api
        .listIssuerCertificates(session.issuer_id)
        .then(setCerts)
        .catch((err) => setError(err.message));
    }
  }, []);

  if (!session) {
    return (
      <div className="card">
        <p>Login required to view transaction status. <Link to="/login">Login</Link></p>
      </div>
    );
  }

  return (
    <div>
      <h2>Transaction Status</h2>
      {error && <div className="error">{error}</div>}
      <div className="card">
        <h3>Blockchain Connection</h3>
        {status ? (
          <>
            <p>Configured: {status.configured ? "Yes" : "No"}</p>
            <p>RPC: {status.rpc_url}</p>
            <p>Contract: {status.contract_address || "—"}</p>
            <p>Chain ID: {status.chain_id ?? "—"}</p>
          </>
        ) : (
          <p className="muted">Loading…</p>
        )}
      </div>
      {session.role === "issuer" && (
        <div className="card">
          <h3>Your Certificates — Latest Transaction</h3>
          {certs.length === 0 ? (
            <p className="muted">No certificates yet.</p>
          ) : (
            <table>
              <thead>
                <tr><th>Certificate ID</th><th>Status</th><th>Transaction</th></tr>
              </thead>
              <tbody>
                {certs.map((c) => (
                  <tr key={c.certificate_id}>
                    <td>{c.certificate_id}</td>
                    <td>{c.blockchain_status}</td>
                    <td style={{ wordBreak: "break-all" }}>
                      {c.blockchain_tx_hash || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="muted">
            blockchain_tx_hash holds the latest transaction for a
            certificate (registration, then revocation if revoked).
          </p>
        </div>
      )}
    </div>
  );
}
