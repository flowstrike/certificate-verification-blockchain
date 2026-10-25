# Runbook — clean local start + demo reproduction

These steps reproduce the system and the Section 19 demo from a clean
local start. “Clean” here means: a fresh Hardhat node (no old contract
or chain state), fresh backend processes, and demo databases whose
tables are created (or cleared) by the steps below. Dependencies are
installed once per folder, as in each folder's README; they are not
reinstalled on every run.

Tested on: Ubuntu, Node v24.22.1, Python 3.12.3, PostgreSQL 16.15.
Exact installed versions for this build are in `SUBMISSION.md`,
Section 4.

## 0. Prerequisites

- Node.js + npm, Python 3.12+, PostgreSQL 16.
- The repo at `certificate-verification-blockchain/`. All commands
  below assume that directory as the working directory, unless a
  different directory is named.

## 1. PostgreSQL

Start PostgreSQL, then create the three databases (once):

```bash
service postgresql start
su postgres -c "psql -c 'CREATE DATABASE certificate_verification;'"
su postgres -c "psql -c 'CREATE DATABASE cert_verify_test;'"
su postgres -c "psql -c 'CREATE DATABASE certificate_demo;'"
```

The backend's local-demo default database user is `postgres` with
password `postgres` (see `backend/README.md`). Change it via the
`DATABASE_URL` environment variable for any real use.

## 2. Blockchain — Hardhat node + deploy

In one terminal:

```bash
cd blockchain
npm install
npx hardhat node
```

Leave that terminal running. In a second terminal:

```bash
cd blockchain
npx hardhat run scripts/deploy.js --network localhost
```

Record the contract address from the output, for example:

```
CertificateVerification deployed to: 0x5FbDB2315678afecb367f032d93F642f64180aa3
```

That address is **not permanent**: it is the first deployment on a
fresh local node. Restarting the node loses it, so redeploy and record
the new address. The backend and frontend both need the current
address.

## 3. Backend — FastAPI

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/certificate_verification \
  CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3 \
  RPC_URL=http://127.0.0.1:8545 \
  .venv/bin/uvicorn app.main:app --port 8000
```

Check health:

```bash
curl http://127.0.0.1:8000/health
# expected: {"status":"ok","database":"connected"}
```

API docs (interactive): `http://localhost:8000/docs`.

If `CONTRACT_ADDRESS` is not set, blockchain endpoints return HTTP
503 rather than fake results. That is intentional.

Demo logins (demo only, override via `ADMIN_EMAIL` / `ADMIN_PASSWORD`
for the Admin account):

- Admin: `admin@demo.local` / `admin123`
- Issuer (created and authorized through the Admin dashboard or API):
  `demo-issuer@demo.local` / `demo123` in the demo script

Backend tokens are in-memory, valid 24 hours, and lost on restart.
Log in again after restarting the backend.

## 4. Frontend — React

```bash
cd frontend
npm install
cp .env.example .env
```

Edit `.env`:

```
VITE_API_URL=http://127.0.0.1:8000
VITE_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
VITE_RPC_URL=http://127.0.0.1:8545
```

Use the contract address from step 2, not the example above. Then:

```bash
npm run dev    # http://localhost:5173
```

MetaMask demo setup (local Hardhat network): RPC
`http://127.0.0.1:8545`, Chain ID `31337`, import Hardhat account 1
as the issuer wallet. These are public test accounts only, never real
funds. If MetaMask is not available, the Register and Revoke pages
also accept a manually pasted transaction hash (from
`blockchain/scripts/submit_tx.js`) plus the backend confirm step.

Note: on this machine Vite binds IPv6 localhost, so if
`curl 127.0.0.1:5173` fails, use `curl localhost:5173` instead. That
is a local networking quirk, not an app bug.

## 5. Demo — Section 19 acceptance (automated)

One-time demo setup:

```bash
cd backend && .venv/bin/pip install reportlab
```

Run (from the repo root; the script starts its own Hardhat node and
backend on port 8001, so stop any node/backend on those ports first,
or let the script's ports conflict visibly and stop them):

```bash
backend/.venv/bin/python demo/run_demo.py
```

Expected output ends with:

```
[demo] Overall: ALL CASES PASS
```

and the evidence is written to `demo/DEMO_RESULT.md` (10 certificates,
their IDs, hashes, transaction hashes, and all 7 cases plus 2 extras).
The script stops its Hardhat node and backend at the end.

To show the same certificates in the frontend afterwards:

```bash
backend/.venv/bin/python demo/run_demo.py --keep-servers
```

This leaves the node (port 8545) and backend (port 8001) running.
Set the frontend `.env` to `VITE_API_URL=http://127.0.0.1:8001` and
the contract address printed by the run, then `npm run dev` and
follow the presenter checklist in `demo/README.md` (Issuer login
shows 10 certificates: 9 ACTIVE, 1 REVOKED; Verify page shows VALID /
MODIFIED / NOT FOUND as listed there).

Re-running the demo generates new Certificate IDs and transaction
hashes. That is expected — `DEMO_RESULT.md` is evidence for the run
that produced it.

## 6. Tests (re-verification)

```bash
# Backend: 24 tests expected to pass
cd backend
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/cert_verify_test \
  CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3 \
  .venv/bin/python -m pytest tests/ -q

# Contract: 11 tests expected to pass
cd ../blockchain
npx hardhat test

# Frontend build: expected to pass
cd ../frontend
npm run build
```

## 7. Troubleshooting

- **Backend returns 503 on blockchain endpoints:** `CONTRACT_ADDRESS`
  is not set, or the Hardhat node was restarted and the contract was
  not redeployed. Redeploy (step 2) and restart the backend with the
  new address.
- **A certificate that was ACTIVE now shows NOT FOUND:** the Hardhat
  node was restarted, so on-chain records are gone. The database still
  has the metadata, but the blockchain is the source of truth for
  verification. Redeploy and re-register.
- **An original file verifies as MODIFIED:** the file was re-saved or
  edited, even slightly. SHA-256 is of the exact bytes. Use the
  byte-identical original file.
- **Modified file verifies as NOT FOUND:** no Certificate ID was
  supplied (see `SUBMISSION.md`, Section 7). Enter the ID to get
  MODIFIED.
- **Login fails after a backend restart:** tokens are in-memory and
  lost on restart. Log in again.
- **Frontend shows a setup message on register/revoke:** 
  `VITE_CONTRACT_ADDRESS` is empty in `frontend/.env`. Set it to the
  current deployed address and restart `npm run dev`.
- **Port already in use (8545 or 8001):** a previous Hardhat node or
  backend is still running. Stop it, or check with
  `curl http://127.0.0.1:8545` / `curl http://127.0.0.1:8001/health`
  and stop the leftover process before re-running.
