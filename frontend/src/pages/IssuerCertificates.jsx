import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { getSession } from "../lib/auth";

export default function IssuerCertificates() {
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

  return (
    <div>
      <h2>Issued Certificates</h2>
      {error && <div className="error">{error}</div>}
      {certs.length === 0 ? (
        <p className="muted">No certificates yet.</p>
      ) : (
        <table>
          <thead>
            <tr><th>Certificate ID</th><th>Student</th><th>Course</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {certs.map((c) => (
              <tr key={c.certificate_id}>
                <td>{c.certificate_id}</td>
                <td>{c.student_name}</td>
                <td>{c.course}</td>
                <td>{c.blockchain_status}</td>
                <td>
                  <a href={api.downloadUrl(c.certificate_id)} target="_blank" rel="noreferrer">
                    Download
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p><Link to="/register">Register a new certificate</Link></p>
    </div>
  );
}
