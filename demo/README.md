# Phase 6 — Acceptance Demonstration (notes, Section 19)

## What this is

`run_demo.py` runs the Section 19 acceptance demonstration automatically
and writes the evidence to `DEMO_RESULT.md`. It does not mock any case:
registration, verification, revocation, and the unauthorized attempt all
go through the real backend, the real contract, and real transactions
on a local Hardhat node.

## Run it (automated proof)

One-time setup:

```bash
su postgres -c "createdb certificate_demo"
cd backend && .venv/bin/pip install reportlab
```

Run:

```bash
cd /path/to/certificate-verification-blockchain
backend/.venv/bin/python demo/run_demo.py
```

The script starts its own Hardhat node and backend (port 8001, database
`certificate_demo`), registers 10 synthetic certificates, runs all
7 cases, runs `npx hardhat test`, and stops both servers at the end.
It exits non-zero if any case fails. The result log is
`demo/DEMO_RESULT.md`, and the 10 synthetic PDFs are in
`demo/certificates/` (each PDF is labelled “synthetic sample” inside).

## The 7 cases, in order

1. **Register 10 certificates** — upload + register tx + backend confirm,
   all 10 ACTIVE.
2. **Original certificate** — upload the original PDF, no ID → VALID.
3. **Modified certificate** — one byte changed in the PDF (first letter
   of the student's name, same length, PDF still valid), uploaded **with
   its Certificate ID** → MODIFIED. The ID is required: a modified
   file's new fingerprint alone cannot identify its original (Phase 5).
4. **Revoked certificate** — revoke one certificate, then upload its
   original PDF → REVOKED.
5. **Unknown Certificate ID** — `CERT-UNKNOWN`, never registered →
   record lookup 404, verification NOT FOUND.
6. **Unauthorized issue attempt** — REJECTED twice, for real: a PENDING
   issuer's backend upload → 403, and an unauthorised wallet's contract
   register → revert. No certificate is created by either attempt.
7. **Smart-contract permissions** — `npx hardhat test`, 11 passing,
   0 failing (Phase 1 tests, including unauthorised register/revoke).

The script also checks two extras: a QR link (`/verify?id=…`) opens the
record, and the verification history contains all four results.

## Show it in the frontend (live presentation)

```bash
backend/.venv/bin/python demo/run_demo.py --keep-servers
```

This leaves the Hardhat node (port 8545) and backend (port 8001)
running, and prints the contract address from the run. Then:

```bash
cd frontend
# set VITE_CONTRACT_ADDRESS to the contract address from the run, in .env
npm run dev   # http://localhost:5173
```

Presenter checklist, using the IDs in `DEMO_RESULT.md`:

- Log in as Issuer (`demo-issuer@demo.local` / `demo123`) — Issuer
  Dashboard shows 10 certificates (9 ACTIVE, 1 REVOKED).
- Open Student, enter the first Certificate ID — Record Found, QR code,
  download.
- Open Verify, upload the original first PDF — VALID.
- Open Verify, upload `cert-01-modified.pdf` with the first Certificate
  ID — MODIFIED.
- Open Verify, enter `CERT-UNKNOWN` — NOT FOUND.
- Log in as Admin (`admin@demo.local` / `admin123`) — Admin Dashboard
  shows the issuers, including the PENDING one from case 6, which was
  never authorized.

Stop the servers with Ctrl+C in the terminals that started them, or
kill the Hardhat node and backend processes when you are done.

## Re-running

Certificate IDs are generated randomly and transaction hashes come from
a fresh local chain, so every run produces different IDs and hashes.
That is expected — `DEMO_RESULT.md` is the evidence for the run that
produced it, not a fixed fixture. Re-running overwrites it.
