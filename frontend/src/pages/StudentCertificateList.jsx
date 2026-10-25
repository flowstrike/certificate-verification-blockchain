import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { api } from "../lib/api";

// Student responsibilities, notes Section 4C: view certificate details,
// download certificate, access Certificate ID, access QR code, share
// the certificate reference. No student login (confirmed Phase 0):
// a student opens a certificate with its ID or QR code.
export default function StudentCertificateList() {
  const [certId, setCertId] = useState("");
  const [cert, setCert] = useState(null);
  const [error, setError] = useState("");

  async function lookup(e) {
    e.preventDefault();
    setError("");
    setCert(null);
    try {
      setCert(await api.getCertificate(certId.trim()));
    } catch (err) {
      setError(err.message);
    }
  }

  const verifyUrl = cert
    ? `${window.location.origin}/verify?id=${cert.certificate_id}`
    : "";

  return (
    <div>
      <h2>Student Certificate</h2>
      <p className="muted">
        Enter a Certificate ID (or scan its QR code, which opens the
        verification page with the same ID). This shows the record only —
        it does not by itself prove an uploaded file is valid.
      </p>
      {error && <div className="error">{error}</div>}
      <div className="card">
        <form onSubmit={lookup}>
          <label>Certificate ID</label>
          <input value={certId} onChange={(e) => setCertId(e.target.value)} placeholder="CERT-XXXXXX" required />
          <button>View Certificate</button>
        </form>
      </div>
      {cert && (
        <div className="card">
          <h3>Record Found</h3>
          <p>Certificate ID: {cert.certificate_id}</p>
          <p>Student Name: {cert.student_name}</p>
          <p>Course: {cert.course}</p>
          <p>College: {cert.college}</p>
          <p>Issue Date: {cert.issue_date}</p>
          <p>Status: {cert.blockchain_status}</p>
          <p>
            <a href={api.downloadUrl(cert.certificate_id)} target="_blank" rel="noreferrer">
              Download Certificate
            </a>
          </p>
          <QRCodeSVG value={verifyUrl} size={180} />
          <p className="muted">
            Share this reference: {verifyUrl}
            <button
              className="secondary"
              style={{ marginLeft: 8 }}
              onClick={() => navigator.clipboard?.writeText(verifyUrl)}
            >
              Copy Link
            </button>
          </p>
        </div>
      )}
    </div>
  );
}
