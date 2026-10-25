# Testing Guide — how to run it and what to test

You are right: the root README was a project plan, not a testing
guide, and the logins were buried in `submission/RUNBOOK.md`. This
file is the one to follow. Read it top to bottom the first time.

## Important first: the IDs in the repo are NOT yours to test

`demo/DEMO_RESULT.md` in this repo lists Certificate IDs from a run
on another machine (for example `CERT-I3ZZDD`). Those IDs and their
PDFs do **not** exist on your machine, because the demo PDFs are not
in the repo and every demo run creates new random IDs.

**Do not test those old IDs.** Run the demo yourself (step 3 below),
then test the IDs in **your own** new `demo/DEMO_RESULT.md`.

## 0. What you need installed

- Node.js + npm
- Python 3.12+
- PostgreSQL 16 (running, with a user you can connect as)

The backend demo default is PostgreSQL user `postgres`, password
`postgres`, database `certificate_demo` for the demo. If your
PostgreSQL user/password are different, set `DATABASE_URL` to match
when you start the backend (see step 3 — the demo script uses the
backend's configured database; the default in `backend/app/config.py`
is the demo one).

## 1. Clone and install (once)

```bash
git clone https://github.com/flowstrike/certificate-verification-blockchain.git
cd certificate-verification-blockchain

cd blockchain && npm install && cd ..
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pip install reportlab && cd ..
cd frontend && npm install && cd ..
```

Create the demo database (once, adjust for your PostgreSQL setup):

```bash
psql -c "CREATE DATABASE certificate_demo;"
```

## 2. Logins (demo only, never real accounts)

These work only while the backend is running, and only after the
step that creates them:

| Who | Email | Password | When it exists |
| --- | --- | --- | --- |
| Admin | `admin@demo.local` | `admin123` | As soon as the backend starts (built-in demo default) |
| Issuer | `demo-issuer@demo.local` | `demo123` | Only after the demo script runs (step 3) — the script creates and authorizes this issuer |

If you start the backend manually without running the demo, the
Issuer login does **not** exist yet. Log in as Admin first, then
create and authorize an issuer from the Admin dashboard (or run the
demo, which does it for you).

Tokens are in-memory and last 24 hours. After a backend restart,
log in again — an old token will fail.

## 3. Easiest path: run the demo, then open the frontend

From the repo root. The script starts its own Hardhat node and
backend on port **8001**, registers 10 synthetic certificates, and
leaves both servers running so you can test in the browser:

```bash
backend/.venv/bin/python demo/run_demo.py --keep-servers
```

Wait for this at the end:

```
[demo] Overall: ALL CASES PASS
```

It also prints the contract address. Copy it. Then open
`demo/DEMO_RESULT.md` — this is now **your** run. Note:

- The **first** certificate in the table (row 1, e.g. Aarav Sharma
  in the sample run) — its ID and its file `demo/certificates/cert-01.pdf`
- The **modified** file `demo/certificates/cert-01-modified.pdf`
  (same certificate, one byte changed)
- The **revoked** certificate (row 2 in the sample run, Priya Patel)
  — its ID and its file `demo/certificates/cert-02.pdf`

In a new terminal, start the frontend pointing at the demo backend:

```bash
cd frontend
cp .env.example .env
```

Edit `.env` to exactly this (use **your** contract address from the
demo output, and port **8001**, not 8000):

```
VITE_API_URL=http://127.0.0.1:8001
VITE_CONTRACT_ADDRESS=<contract address printed by the demo run>
VITE_RPC_URL=http://127.0.0.1:8545
```

Then:

```bash
npm run dev
```

Open http://localhost:5173 — **on your own computer**, not on a
remote machine. After changing `.env`, restart `npm run dev`.

## 4. What to test, in order (use YOUR IDs from step 3)

1. **Issuer dashboard** — Log in as Issuer
   (`demo-issuer@demo.local` / `demo123`). You should see
   10 certificates: 9 ACTIVE, 1 REVOKED.
2. **Student lookup (no login needed)** — Open Student, enter the
   first Certificate ID from your `DEMO_RESULT.md`.
   Expected: **Record Found**, with QR code and download.
   This is a lookup only — it is NOT file verification.
3. **Verify original = VALID** — Open Verify, upload
   `demo/certificates/cert-01.pdf` (the original first file),
   no ID needed. Expected: **VALID**.
4. **Verify modified = MODIFIED** — Open Verify, upload
   `demo/certificates/cert-01-modified.pdf` **and enter the first
   Certificate ID**. Expected: **MODIFIED**.
   The ID is required here: a modified file's new fingerprint
   alone cannot identify its original, so without an ID it shows
   NOT FOUND instead. That is by design, not a bug.
5. **Verify revoked = REVOKED** — Open Verify, upload the revoked
   certificate's original file (`cert-02.pdf` in the sample run).
   Expected: **REVOKED**.
6. **Verify unknown = NOT FOUND** — Open Verify, enter
   `CERT-UNKNOWN` (never registered). Expected: **NOT FOUND**.
7. **Admin dashboard** — Log in as Admin
   (`admin@demo.local` / `admin123`). You should see the issuers,
   including the PENDING one the demo tried (and failed) to issue
   with — it was never authorized, so it issued nothing.

## 5. If you want to test without the demo (manual path)

Follow `submission/RUNBOOK.md` instead: start a Hardhat node,
deploy the contract, start the backend on port 8000 with that
contract address, set the frontend `.env` to port 8000 and the same
address, log in as Admin, create + authorize an issuer, then use
the Register page to upload a real PDF. You will need MetaMask
(local Hardhat network, RPC `http://127.0.0.1:8545`, Chain ID
`31337`, Hardhat account 1 as issuer wallet) — or paste a
transaction hash manually from `blockchain/scripts/submit_tx.js`
and use the backend confirm step. The demo path (step 3) is much
easier for a first test.

## 6. Common problems

- **Login fails:** backend was restarted (tokens are lost) — log
  in again. Issuer login fails before the demo ran — the issuer
  does not exist yet (see step 2).
- **Backend returns 503 on blockchain pages:** the contract
  address is missing or the Hardhat node was restarted. Redeploy
  and restart the backend with the new address.
- **A certificate that was ACTIVE now shows NOT FOUND:** the
  Hardhat node was restarted, so on-chain records are gone.
  Re-run the demo (it starts a fresh node and re-registers).
- **Original file shows MODIFIED:** the file was re-saved or
  edited, even slightly. SHA-256 is of the exact bytes — use the
  byte-identical original from `demo/certificates/`.
- **Modified file shows NOT FOUND:** no Certificate ID was
  entered. Enter the ID (step 4, test 4).
- **Frontend shows a setup message on Register/Revoke:**
  `VITE_CONTRACT_ADDRESS` is empty in `frontend/.env`. Set it
  and restart `npm run dev`.
- **Port already in use (8545 or 8001):** an old Hardhat node or
  backend is still running. Stop it before re-running the demo.
- **Old IDs from the repo's DEMO_RESULT.md don't work:** expected
  — those are from another machine. Re-run the demo and use your
  own new IDs (see the top of this file).
