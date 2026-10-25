import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

// QR Verification Page, notes Section 6. A QR code encodes the
// verification-page URL with the Certificate ID (confirmed Phase 0
// decision 5), so scanning it opens /verify?id=CERT-... . This page
// handles the same ID directly, and also links to the full verification
// page. A phone camera does the actual QR scanning — this web page
// does not need camera access.
export default function QrVerification() {
  const [params] = useSearchParams();
  const [certId, setCertId] = useState(params.get("id") || "");
  const [record, setRecord] = useState(null);
  const [error, setError] = useState("");

  async function lookup(id) {
    setError("");
    setRecord(null);
    try {
      setRecord(await api.getCertificate(id));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (params.get("id")) lookup(params.get("id"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <h2>QR Verification</h2>
      <p className="muted">
        Scan a certificate QR code with your phone camera to open the
        verification page for that Certificate ID. Or enter the ID below.
      </p>
      {error && <div className="error">{error}</div>}
      <div className="card">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            lookup(certId.trim());
          }}
        >
          <label>Certificate ID (from QR code)</label>
          <input value={certId} onChange={(e) => setCertId(e.target.value)} placeholder="CERT-XXXXXX" required />
          <button>Open Certificate</button>
        </form>
      </div>
      {record && (
        <div className="card">
          <div className="success">Record Found</div>
          <p>
            {record.certificate_id} — {record.student_name} — {record.course} —{" "}
            {record.college}
          </p>
          <p>
            <Link to={`/verify?id=${record.certificate_id}`}>
              Go to full verification page
            </Link>
          </p>
        </div>
      )}
    </div>
  );
}
