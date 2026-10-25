import { useState } from "react";
import { Link } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { api } from "../lib/api";
import { getSession } from "../lib/auth";
import {
  connectWallet,
  isBlockchainConfigured,
  registerOnChain,
} from "../lib/blockchain";

// Registration form fields, notes Section 14: Student Name, Course,
// College, Issue Date, Certificate PDF. After success the notes show:
// Certificate ID, SHA-256, Transaction, Status ACTIVE, QR Code.
export default function RegisterCertificate() {
  const session = getSession();
  const [form, setForm] = useState({
    student_name: "",
    course: "",
    college: "",
    issue_date: "",
  });
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [txHash, setTxHash] = useState("");
  const [wallet, setWallet] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  if (session?.role !== "issuer") {
    return (
      <div className="card">
        <p>Issuer login required. <Link to="/login">Login</Link></p>
      </div>
    );
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    setResult(null);
    if (!file) {
      setError("Choose a certificate PDF.");
      return;
    }
    setBusy(true);
    try {
      const data = new FormData();
      data.append("student_name", form.student_name);
      data.append("course", form.course);
      data.append("college", form.college);
      data.append("issue_date", form.issue_date);
      data.append("issuer_id", String(session.issuer_id));
      data.append("file", file);
      const cert = await api.uploadCertificate(data);
      setResult(cert);
      setMessage(
        "CERTIFICATE REGISTERED SUCCESSFULLY in the backend. " +
          "It is NOT on-chain yet — complete the blockchain step below to make it ACTIVE."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function doWalletRegister() {
    setError("");
    setMessage("");
    try {
      const address = await connectWallet();
      setWallet(address);
      const hash = await registerOnChain(result.certificate_id, result.sha256_hash);
      setTxHash(hash);
      const confirmed = await api.confirmBlockchain(result.certificate_id, hash);
      setResult(confirmed);
      setMessage("Certificate is now ACTIVE on the blockchain.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function doManualConfirm() {
    setError("");
    try {
      if (!txHash.trim()) throw new Error("Enter a transaction hash first.");
      const confirmed = await api.confirmBlockchain(result.certificate_id, txHash.trim());
      setResult(confirmed);
      setMessage("Certificate is now ACTIVE on the blockchain.");
    } catch (err) {
      setError(err.message);
    }
  }

  const verifyUrl = result
    ? `${window.location.origin}/verify?id=${result.certificate_id}`
    : "";

  return (
    <div>
      <h2>Register Certificate</h2>
      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}

      <div className="card">
        <form onSubmit={submit}>
          <label>Student Name</label>
          <input value={form.student_name} onChange={(e) => setForm({ ...form, student_name: e.target.value })} required />
          <label>Course</label>
          <input value={form.course} onChange={(e) => setForm({ ...form, course: e.target.value })} required />
          <label>College</label>
          <input value={form.college} onChange={(e) => setForm({ ...form, college: e.target.value })} required />
          <label>Issue Date</label>
          <input type="date" value={form.issue_date} onChange={(e) => setForm({ ...form, issue_date: e.target.value })} required />
          <label>Certificate PDF</label>
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
          <button disabled={busy || session.authorization_status !== "AUTHORIZED"}>
            {busy ? "Registering…" : "Register Certificate"}
          </button>
        </form>
      </div>

      {result && (
        <div className="card">
          <h3>Certificate Registered</h3>
          <p>Certificate ID: {result.certificate_id}</p>
          <p style={{ wordBreak: "break-all" }}>SHA-256: {result.sha256_hash}</p>
          <p>Transaction: {result.blockchain_tx_hash || "— (not on-chain yet)"}</p>
          <p>Status: {result.blockchain_status}</p>
          {result.blockchain_status === "ACTIVE" && (
            <>
              <QRCodeSVG value={verifyUrl} size={180} />
              <p className="muted">QR Code — scans to: {verifyUrl}</p>
            </>
          )}

          {result.blockchain_status !== "ACTIVE" && (
            <>
              <h4>Blockchain step</h4>
              <p className="muted">
                Option 1 — with MetaMask (issuer wallet must be the authorised
                wallet): connect, then send the register transaction.
              </p>
              <button onClick={doWalletRegister} disabled={!isBlockchainConfigured()}>
                Connect Wallet &amp; Register On-Chain
              </button>
              {!isBlockchainConfigured() && (
                <p className="muted">
                  Contract address is not configured (VITE_CONTRACT_ADDRESS).
                  Use Option 2 until it is set.
                </p>
              )}
              {wallet && <p className="muted">Connected wallet: {wallet}</p>}
              <p className="muted">
                Option 2 — without MetaMask: run
                blockchain/scripts/submit_tx.js (MODE=register) with this
                Certificate ID and hash, then paste the transaction hash
                here and confirm.
              </p>
              <label>Transaction Hash</label>
              <input value={txHash} onChange={(e) => setTxHash(e.target.value)} placeholder="0x…" />
              <button onClick={doManualConfirm} className="secondary">
                Confirm On-Chain Registration
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
