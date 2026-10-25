import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { getSession } from "../lib/auth";

export default function VerificationHistory() {
  const session = getSession();
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (session) {
      api
        .listVerificationLogs()
        .then(setLogs)
        .catch((err) => setError(err.message));
    }
  }, []);

  if (!session) {
    return (
      <div className="card">
        <p>Login required to view verification history. <Link to="/login">Login</Link></p>
      </div>
    );
  }

  return (
    <div>
      <h2>Verification History</h2>
      <p className="muted">
        Every verification attempt is recorded here (notes, Section 8:
        VerificationLog), including VALID, MODIFIED, REVOKED, and
        NOT FOUND results.
      </p>
      {error && <div className="error">{error}</div>}
      {logs.length === 0 ? (
        <p className="muted">No verification history yet.</p>
      ) : (
        <table>
          <thead>
            <tr><th>Verification ID</th><th>Certificate ID</th><th>Date</th><th>Result</th></tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{log.id}</td>
                <td>{log.certificate_id}</td>
                <td>{new Date(log.verification_date).toLocaleString()}</td>
                <td>{log.verification_result}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p><Link to="/verify">Go to verification page</Link></p>
    </div>
  );
}
