import { Link } from "react-router-dom";

// Design from the notes, Section 14 (Home Page).
export default function Home() {
  return (
    <div className="card" style={{ textAlign: "center", padding: "48px 16px" }}>
      <h1>Verify Academic Certificates</h1>
      <h2 style={{ fontWeight: 400 }}>Securely Using Blockchain</h2>
      <p className="muted">
        A college registers a certificate. Its fingerprint is stored on a
        local blockchain, and the details are stored in a database. Anyone
        can check an uploaded certificate against that record.
      </p>
      <Link to="/verify">
        <button>Verify Certificate</button>
      </Link>
      <p className="muted" style={{ marginTop: 24 }}>
        Verifiers need no login. Students can open their certificate with
        its Certificate ID or QR code. Issuers and Admins log in above.
      </p>
    </div>
  );
}
