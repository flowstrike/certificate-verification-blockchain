# Frontend — React + Vite (Phase 4)

All 11 frontend pages from the notes, Section 6:

| Page | Route | Notes design? |
|---|---|---|
| Home Page | `/` | Yes, Section 14 |
| Login Page | `/login` | — |
| Admin Dashboard | `/admin` | — |
| Issuer Dashboard | `/issuer` | Yes, Section 14 |
| Certificate Registration Page | `/register` | Yes, Section 14 |
| Student Certificate List | `/student` | — |
| Certificate Verification Page | `/verify` | Yes, Section 14 (public) |
| Revocation Page | `/revoke` | — |
| Transaction Status | `/transactions` | — |
| Verification History | `/history` | — |
| QR Verification Page | `/qr` | — |

Issuer Certificates (`/issuer/certificates`) is the Issuer Dashboard's
“Certificates” view from the Section 14 sidebar.

## What each page does

- **Home:** hero from Section 14, “Verify Certificate” button.
- **Login:** Admin / Issuer email + password (backend `/auth/login`).
  Students have no login (ID / QR), verifiers are public.
- **Admin:** view issuers, add an issuer (college, wallet, email,
  password), authorize an issuer in the database.
- **Issuer Dashboard:** Total / Active / Revoked counts, Register action,
  Recent Certificates. A PENDING issuer sees a pending warning and
  cannot register.
- **Register:** Student Name, Course, College, Issue Date, PDF (Section 14).
  After backend registration it shows Certificate ID, SHA-256,
  Transaction, Status, and a QR code — but only ACTIVE after the
  blockchain step. Blockchain step, two options:
  1. MetaMask: connect the authorised issuer wallet and send the
     register transaction; the frontend then calls confirm-blockchain.
  2. Without MetaMask: run `blockchain/scripts/submit_tx.js`
     (MODE=register), paste the transaction hash, and confirm.
- **Student:** enter a Certificate ID, view details, download, QR code,
  share link. Record lookup only — never labelled VALID.
- **Verify (public):** ID lookup (Record Found / Not Found, never
  VALID) + real file verification via POST /verify: VALID / MODIFIED /
  REVOKED / NOT FOUND, with every attempt logged. To detect MODIFIED,
  enter the Certificate ID — a modified file's new fingerprint alone
  cannot identify its original (see backend README, Phase 5).
- **Revoke:** select a certificate, revoke via MetaMask or via
  submit_tx.js + manual confirm. Status becomes REVOKED; the record
  is not deleted.
- **Transactions:** blockchain connection status + latest transaction
  per issuer certificate.
- **History:** lists VerificationLog rows written by every /verify
  attempt.
- **QR:** a QR code encodes the verification URL with the Certificate
  ID (confirmed Phase 0 decision 5). Scanning it with a phone camera
  opens `/verify?id=CERT-...`; this page also accepts the ID directly.

## Versions recorded at install

- React 18.3.1, react-router-dom 6.30.6, ethers 6.17.0,
  qrcode.react 4.2.0, Vite 5.4.21, Node v24.22.1

## Run locally (full stack, in order)

```bash
# 1. PostgreSQL running, backend on :8000 (see backend/README.md)
# 2. Hardhat node + deploy (see blockchain/README.md), note the address
# 3. Frontend
cd frontend
npm install
cp .env.example .env
# Edit .env: set VITE_CONTRACT_ADDRESS to the deployed address
npm run dev        # http://localhost:5173
npm run build      # production build check
```

## MetaMask setup for the local demo

1. Install MetaMask, add a network: Hardhat Local,
   RPC http://127.0.0.1:8545, Chain ID 31337, currency ETH.
2. Import Hardhat account 1 (the authorised issuer in the demo).
   These are Hardhat's public local-test accounts — never real funds,
   never use a real wallet here.
3. The wallet address in MetaMask must match the issuer's wallet
   address in the database, or the contract will reject the transaction
   (only authorised issuers may register/revoke).

## Phase 4 supporting backend work (auth)

Login needs a real backend, so Phase 4 also added backend auth
(`backend/app/auth.py`): PBKDF2 password hashes, `/auth/login`,
in-memory tokens (24h, do not survive a restart), and protection for
admin endpoints (create/authorize/list issuers) and issuer endpoints
(upload, confirm) — an issuer can only act under their own issuer_id.
Public endpoints (record lookup, download, on-chain reads) stay public.
Demo Admin: admin@demo.local / admin123 (override with ADMIN_EMAIL /
ADMIN_PASSWORD env — demo defaults only, see backend README).

## Phase 4 exit criteria — verified 2026-10-25

- [x] All 11 pages exist and are routed (plus Issuer Certificates view).
- [x] `npm run build` passes; preview server serves the app (HTTP 200
      on localhost:5173); all page titles are present in the built bundle.
- [x] Admin can view and authorize issuers (backend tests + live check).
- [x] Issuer can view issued certificates and transaction status.
- [x] Student can view details, download, and access Certificate ID
      and QR code.
- [x] Backend tests still pass after auth (17 pytest tests) and the
      Phase 3 live check still passes (with login + tokens).
- [x] Full file verification (VALID / MODIFIED / REVOKED + logging) —
      Phase 5, via POST /verify (see backend README).
