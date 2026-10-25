import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { getSession } from "../lib/auth";
import {
  connectWallet,
  isBlockchainConfigured,
  revokeOnChain,
} from "../lib/blockchain";

// Revocation flow, notes Section 17: Issuer Login -> Select Certificate
// -> Click Revoke -> Check Issuer Authorization -> Call Smart Contract
// -> ACTIVE -> REVOKED -> Record Blockchain Transaction -> Status Updated.
// The record is not deleted; its status changes.
export default function Revocation() {
  const session = getSession();
  const [certs, setCerts] = useState([]);
  const [selected, setSelected] = useState("");
  const [txHash, setTxHash] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    try {
      setCerts(await api.listIssuerCertificates(session.issuer_id));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (session?.issuer_id) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (session?.role !== "issuer") {
    return (
      <div className="card">
        <p>Issuer login required. <Link to="/login">Login</Link></p>
      </div>
    );
  }

  async function doWalletRevoke() {
    setError("");
    try {
      if (!selected) throw new Error("Select a certificate first.");
      await connectWallet();
      const hash = await revokeOnChain(selected);
      setTxHash(hash);
      await api.confirmRevocation(selected, hash);
      setMessage("Certificate status updated to REVOKED.");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function doManualConfirm() {
    setError("");
    try {
      if (!selected || !txHash.trim()) {
        throw new Error("Select a certificate and enter a transaction hash.");
      }
      await api.confirmRevocation(selected, txHash.trim());
      setMessage("Certificate status updated to REVOKED.");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <h2>Revoke Certificate</h2>
      <p className="muted">
        Revocation does not delete the record. Its status changes from
        ACTIVE to REVOKED, so the previous ledger history remains.
      </p>
      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}
      <div className="card">
        <label>Select Certificate</label>
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value="">— Select —</option>
          {certs.map((c) => (
            <option key={c.certificate_id} value={c.certificate_id}>
              {c.certificate_id} — {c.student_name} ({c.blockchain_status})
            </option>
          ))}
        </select>
        <button onClick={doWalletRevoke} disabled={!isBlockchainConfigured()}>
          Revoke On-Chain (MetaMask)
        </button>
        <p className="muted">
          Or, after running submit_tx.js (MODE=revoke), paste the
          transaction hash and confirm:
        </p>
        <label>Transaction Hash</label>
        <input value={txHash} onChange={(e) => setTxHash(e.target.value)} placeholder="0x…" />
        <button onClick={doManualConfirm} className="secondary">
          Confirm Revocation
        </button>
      </div>
    </div>
  );
}
