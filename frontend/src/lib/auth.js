// Session storage for the local demo. The token comes from the backend
// /auth/login endpoint (Phase 4 backend auth). Student and Verifier have
// no login: they use Certificate ID / QR and the public pages.
const KEY = "cert-verify-session";

export function getSession() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "null");
  } catch {
    return null;
  }
}

export function saveSession(session) {
  localStorage.setItem(KEY, JSON.stringify(session));
}

export function clearSession() {
  localStorage.removeItem(KEY);
}

export function authHeaders() {
  const session = getSession();
  return session?.token ? { Authorization: `Bearer ${session.token}` } : {};
}
