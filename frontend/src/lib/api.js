import { authHeaders } from "./auth";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { ...(options.headers || {}) },
  });
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = { detail: text };
  }
  if (!res.ok) {
    throw new Error(body?.detail || `Request failed (${res.status})`);
  }
  return body;
}

async function authed(path, options = {}) {
  return request(path, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
}

export const api = {
  // Auth
  login: (email, password) =>
    request("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),

  // Admin
  listIssuers: () => authed("/issuers"),
  createIssuer: (payload) =>
    authed("/issuers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  authorizeIssuer: (id) =>
    authed(`/issuers/${id}/authorize`, { method: "PATCH" }),

  // Certificates (issuer)
  uploadCertificate: (formData) =>
    fetch(`${API}/certificates`, {
      method: "POST",
      headers: { ...authHeaders() },
      body: formData,
    }).then(async (res) => {
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || `Upload failed (${res.status})`);
      return body;
    }),
  listIssuerCertificates: (issuerId) =>
    authed(`/issuers/${issuerId}/certificates`),
  confirmBlockchain: (certId, transaction_hash) =>
    authed(`/certificates/${certId}/confirm-blockchain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transaction_hash }),
    }),
  confirmRevocation: (certId, transaction_hash) =>
    authed(`/certificates/${certId}/confirm-revocation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transaction_hash }),
    }),

  // Public: record lookup, download, on-chain reads, verification
  verifyCertificate: (formData) =>
    fetch(`${API}/verify`, { method: "POST", body: formData }).then(
      async (res) => {
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.detail || `Verify failed (${res.status})`);
        return body;
      }
    ),
  getCertificate: (certId) => request(`/certificates/${certId}`),
  downloadUrl: (certId) => `${API}/certificates/${certId}/download`,
  getBlockchainRecord: (certId) => request(`/certificates/${certId}/blockchain`),
  getBlockchainStatus: () => request("/blockchain/status"),
  getIssuerBlockchainAuthorized: (issuerId) =>
    request(`/issuers/${issuerId}/blockchain-authorized`),

  // Verification History (Phase 5 writes rows; Phase 4 lists them)
  listVerificationLogs: (certId) =>
    authed(`/verification-logs${certId ? `?certificate_id=${certId}` : ""}`),
};

export { API };
