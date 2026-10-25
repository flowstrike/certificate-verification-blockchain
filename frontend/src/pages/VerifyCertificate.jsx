import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

// Public Certificate Verification Page, notes Section 14: upload a
// certificate PDF and verify. The result can be VALID, MODIFIED,
// REVOKED, or NOT FOUND (notes, Section 16).
//
// This page keeps two things strictly separate (notes, Section 18):
//   A. ID lookup -> "Record Found" / "Not Found" (never VALID).
//   B. File verification -> VALID / MODIFIED / REVOKED / NOT FOUND,
//      from POST /verify, which compares the uploaded file's SHA-256
//      with the on-chain hash and logs the attempt.
//
// One honest rule the page explains: a modified file has a brand-new
// fingerprint, and a fingerprint cannot be reversed to find its
// original. So to get MODIFIED (rather than NOT FOUND) for a suspected
// modified file, enter its Certificate ID so the system knows which
// original to compare it with.
export default function VerifyCertificate() {
  const [params] = useSearchParams();
  const [certId, setCertId] = useState(params.get("id") || "");
  const [record, setRecord] = useState(null);
  const [lookupError, setLookupError] = useState("");
  const [verifyFile, setVerifyFile] = useState(null);
  const [verifyId, setVerifyId] = useState(params.get("id") || "");
  const [result, setResult] = useState(null);
  const [verifyError, setVerifyError] = useState("");
  const [busy, setBusy] = useState(false);

  async function lookup(id) {
    setLookupError("");
    setRecord(null);
    try {
      setRecord(await api.getCertificate(id));
    } catch (err) {
      setLookupError(err.message);
    }
  }

  useEffect(() => {
    if (params.get("id")) lookup(params.get("id"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function verify(e) {
    e.preventDefault();
    setVerifyError("");
    setResult(null);
    if (!verifyFile) {
      setVerifyError("Choose a certificate PDF to verify.");
      return;
    }
    setBusy(true);
    try {
      const data = new FormData();
      if (verifyId.trim()) data.append("certificate_id", verifyId.trim());
      data.append("file", verifyFile);
      setResult(await api.verifyCertificate(data));
    } catch (err) {
      setVerifyError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2>Verify Certificate</h2>
      <p className="muted">Public page — no login needed.</p>

      <div className="card">
        <h3>A. Certificate ID Lookup — Record Only</h3>
        {lookupError && <div className="error">{lookupError}</div>}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            lookup(certId.trim());
          }}
        >
          <label>Certificate ID</label>
          <input value={certId} onChange={(e) => setCertId(e.target.value)} placeholder="CERT-XXXXXX" required />
          <button>Look Up Record</button>
        </form>
        {record && (
          <>
            <div className="success">Record Found</div>
            <p>Student: {record.student_name} — {record.course}</p>
            <p>College: {record.college} — Issue Date: {record.issue_date}</p>
            <p>Database status: {record.blockchain_status}</p>
            <p className="muted">
              “Record Found” is not “VALID”. Only file verification
              below can prove a file is valid.
            </p>
          </>
        )}
      </div>

      <div className="card">
        <h3>B. File Verification — Upload PDF</h3>
        {verifyError && <div className="error">{verifyError}</div>}
        <form onSubmit={verify}>
          <label>Certificate ID (optional, but required to detect MODIFIED)</label>
          <input
            value={verifyId}
            onChange={(e) => setVerifyId(e.target.value)}
            placeholder="CERT-XXXXXX — leave blank to verify by fingerprint alone"
          />
          <label>Certificate PDF</label>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setVerifyFile(e.target.files?.[0] || null)}
            required
          />
          <button disabled={busy}>{busy ? "Verifying…" : "Verify"}</button>
        </form>
        <p className="muted">
          Why the ID matters: a modified file has a new fingerprint that
          matches no original, so without an ID it cannot be identified
          and the result will be NOT FOUND. With the ID, the system
          compares the uploaded fingerprint with that certificate's
          on-chain fingerprint: match = VALID, mismatch = MODIFIED.
          A revoked certificate always returns REVOKED, even if the
          file is byte-identical to the original.
        </p>
        {result && (
          <div>
            <div
              className={
                result.verification_result === "VALID" ? "success" : "error"
              }
            >
              <strong>{result.verification_result.replace("_", " ")}</strong>
            </div>
            {result.certificate_id && <p>Certificate ID: {result.certificate_id}</p>}
            {result.student_name && (
              <p>Student: {result.student_name} — {result.course} — {result.college}</p>
            )}
            <p style={{ wordBreak: "break-all" }}>
              Uploaded SHA-256: {result.uploaded_sha256_hash}
            </p>
            {result.stored_sha256_hash && (
              <p style={{ wordBreak: "break-all" }}>
                On-chain SHA-256: {result.stored_sha256_hash}
              </p>
            )}
            {result.onchain_status && <p>On-chain status: {result.onchain_status}</p>}
            <p className="muted">
              This verification attempt has been recorded in the
              verification history.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
