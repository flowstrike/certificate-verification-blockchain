# Backend — Python + FastAPI + PostgreSQL (Phase 2)

Backend flow, from the notes Section 7, without blockchain wiring yet
(Phase 3):

Receive Certificate → Validate Request → Check Issuer Authorization →
Generate Certificate ID → Calculate SHA-256 Hash → Store Certificate
Metadata + PDF → Return Result.

## Tables (notes, Section 8, plus documented extensions)

- **issuers:** Issuer ID, College Name, Wallet Address, Authorization Status
  (PENDING / AUTHORIZED — values are an implementation choice, the notes
  do not name them), plus `email` / `password_hash` reserved for the
  confirmed Phase 0 login decision (login itself is Phase 4).
- **certificate_metadata:** Certificate ID, Student Name, Course, College
  (from the registration form, Section 14), Certificate File, Issue Date,
  plus `issuer_id`, `sha256_hash`, `blockchain_tx_hash`,
  `blockchain_status` (needed for Phase 3).
- **verification_logs:** Verification ID, Certificate ID, Verification Date,
  Verification Result. Written by the verification endpoint in Phase 5;
  Phase 2 only creates the table.

PDFs are stored on disk in `backend/uploads/` (confirmed Phase 0
decision 4), never on the blockchain. In Phase 2,
`blockchain_status` is `NOT_REGISTERED_ONCHAIN` — a certificate must not
be presented as ACTIVE until Phase 3 registers it on-chain.

## Endpoints (Phase 2)

- `GET /health`
- `POST /issuers` — create issuer (starts PENDING)
- `GET /issuers`
- `PATCH /issuers/{id}/authorize` — Admin authorizes an issuer
- `POST /certificates` — multipart upload: student_name, course, college,
  issue_date, issuer_id, file (PDF). Rejects unauthorized issuers (403)
  and non-PDF files (400). Returns Certificate ID + SHA-256 hash.
- `GET /certificates/{certificate_id}` — record lookup only. Finding a
  record means “Record Found”, not VALID (notes, Section 18).
- `GET /issuers/{id}/certificates`
- `GET /certificates/{certificate_id}/download`

Phase 4 update: `POST /issuers`, `GET /issuers`, and the authorize
endpoint are now Admin-protected (token from `/auth/login`), and
upload / confirm endpoints require an issuer token matching the
issuer_id. See “Phase 4 — auth” below.

## Versions recorded at install (Phase 0, decision 11)

- Python 3.12.3, FastAPI 0.162.0, SQLAlchemy 2.1.6, psycopg2-binary 2.9.13,
  Uvicorn 0.54.0, Pydantic 2.14.1, pytest 9.1.1, PostgreSQL 16.15,
  web3.py 8.0.0 (read-only, Phase 3)

## Run locally

```bash
# 1. PostgreSQL: create the database (once)
#    On Ubuntu/Debian: sudo apt install postgresql
#    Then, as the postgres user:
#      createdb certificate_verification
#    Or set DATABASE_URL to your own database (see .env.example).

# 2. Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/certificate_verification \
  .venv/bin/uvicorn app.main:app --reload --port 8000
```

API docs (interactive): http://127.0.0.1:8000/docs

## Phase 3 — backend ↔ blockchain (done)

Split, per the confirmed Phase 0 decision 2:

1. FastAPI validates, generates the ID, hashes the PDF, stores metadata
   (Phase 2, unchanged).
2. React + ethers.js sends the register / revoke transaction (Phase 4).
   Until the React UI exists, `blockchain/scripts/submit_tx.js` proves
   that ethers.js path with Hardhat's local accounts.
3. The backend NEVER sends a transaction. It only reads the contract
   (`app/blockchain.py`, via web3.py) to verify a claimed transaction
   before updating the database.

New endpoints:

- `GET /blockchain/status` — configured? RPC? Contract address? Chain ID?
- `GET /certificates/{id}/blockchain` — on-chain record (hash, issuer, status)
- `GET /issuers/{id}/blockchain-authorized` — DB authorization vs on-chain
- `POST /certificates/{id}/confirm-blockchain` — body `{transaction_hash}`.
  Checks the receipt, reads the contract, and only marks ACTIVE when
  hash, issuer, and status all match. Otherwise 409 and the DB status
  is left unchanged.
- `POST /certificates/{id}/confirm-revocation` — same, for REVOKED.

Setup: deploy first, then start the backend with the address:

```bash
cd blockchain && npx hardhat node   # terminal 1
npx hardhat run scripts/deploy.js --network localhost   # terminal 2
cd ../backend
CONTRACT_ADDRESS=0x... RPC_URL=http://127.0.0.1:8545 \
  .venv/bin/uvicorn app.main:app --port 8000
```

If `CONTRACT_ADDRESS` is not set, blockchain endpoints return 503
instead of pretending to verify anything. The contract ABI used by the
backend is committed as `app/contract_abi.json` (generated from the
Phase 1 Hardhat artifacts; regenerate it if the contract changes).

## Phase 4 — auth (supporting backend work)

- `POST /auth/login` — Admin (ADMIN_EMAIL / ADMIN_PASSWORD env, demo
  defaults admin@demo.local / admin123) or Issuer (email + PBKDF2
  password hash from the Issuer row). Returns a token + role.
- `GET /auth/me` — validate a token.
- Tokens are in-memory, 24h, and do not survive a backend restart.
  This is a college-demo scheme, not production auth (no JWT, refresh,
  or password reset — the notes do not ask for those).
- Protected: create/list/authorize issuers (Admin only); upload and
  confirm endpoints (issuer token, own issuer_id only).
- Public: record lookup, download, on-chain reads, blockchain status.
- `GET /verification-logs` — list VerificationLog rows (empty until
  Phase 5 writes them).

## Phase 5 — verification, revocation, QR, ID lookup (done)

### POST /verify — Section 16 flow, in order

Upload PDF → SHA-256 → Get Blockchain Record → Record Exists?
(NO → NOT_FOUND) → Revoked? (YES → REVOKED) → Compare Hash
(YES → VALID, NO → MODIFIED). Every attempt is written to
VerificationLog. The endpoint is public (verifier public).

Request: multipart `file` (PDF, required) + `certificate_id`
(optional). Response: `certificate_id`, `verification_result`
(VALID / MODIFIED / REVOKED / NOT_FOUND — API code uses NOT_FOUND
with an underscore; the frontend displays it as “NOT FOUND”),
`uploaded_sha256_hash`, `stored_sha256_hash` (on-chain, if any),
`onchain_status`, `issuer_address`, and student/course/college when
a database record exists.

The blockchain record is the source of truth: a database record with
no on-chain record verifies as NOT_FOUND, and a revoked on-chain
record verifies as REVOKED even for a byte-identical file.

### Why MODIFIED needs a Certificate ID (Phase 5 finding)

A SHA-256 hash is one-way. A modified file has a brand-new hash, and
no lookup can tell which original it was changed from, because the
contract is keyed by Certificate ID, not by hash (notes, Section 9).
So:
- With an ID, the system compares the uploaded hash with that
  certificate's on-chain hash: match = VALID, mismatch = MODIFIED.
- Without an ID, the system first finds a record by the uploaded hash
  in PostgreSQL. If it matches, that ID is used for the on-chain
  check. If nothing matches, no record can be identified, so the
  result is NOT_FOUND — never a guessed MODIFIED.
The frontend Verify page explains this and asks for the ID when a
verifier suspects modification. The Phase 6 demo therefore supplies
the ID for the MODIFIED case.

### ID lookup vs file verification (Section 18)

`GET /certificates/{id}` is record lookup only: it returns metadata
and never a `verification_result` field. Only POST /verify with a
PDF can return VALID. QR codes encode the verification URL with the
ID, so scanning one opens ID lookup — it does not by itself prove
a file is valid.

### Live check

```bash
cd backend
.venv/bin/python tests/phase5_live_check.py
```

It runs: upload → register → confirm ACTIVE → /verify original
= VALID → /verify modified (with ID) = MODIFIED → revoke →
confirm REVOKED → /verify original = REVOKED → /verify unknown ID
= NOT_FOUND → ID lookup = Record Found → history contains all four
results.

## Phase 5 exit criteria — verified 2026-10-25

- [x] Each of the four verification outcomes can be produced on demand.
- [x] ID search and PDF verification show different, correctly worded results.
- [x] A revoked certificate verifies as REVOKED, not VALID, even for a
      byte-identical file.
- [x] Every verification attempt appears in Verification History /
      VerificationLog.
- [x] 24 pytest tests pass (17 previous + 7 new /verify tests) and the
      Phase 5 live check passes.

## Tests

```bash
cd backend
.venv/bin/python -m pytest tests/test_services.py -v   # no database needed
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/cert_verify_test \
  .venv/bin/python -m pytest tests/test_api.py -v     # needs PostgreSQL
```

The API test database is cleared before each test — never point it at
real data.

Live Phase 3 check (starts its own Hardhat node + backend, kills both
on exit — it is not part of the pytest suite because it needs a chain):

```bash
cd backend
.venv/bin/python tests/phase3_live_check.py
```

## Phase 3 exit criteria — verified 2026-10-25

- [x] A registered certificate can be read back from the contract by ID,
      with matching hash, issuer, and ACTIVE status (live check).
- [x] An unauthorized issuer is rejected before a contract write (Phase 2,
      403) and also by the contract (Phase 1 tests).
- [x] A failed / fake contract write does not leave a misleading
      “registered” result — confirm without a real tx returns 409 and
      leaves `blockchain_status` as NOT_REGISTERED_ONCHAIN.
- [x] Revocation via ethers.js + confirm marks REVOKED, with the original
      hash still readable on-chain.

## Phase 2 exit criteria — verified 2026-10-25

- [x] Uploading a PDF returns a Certificate ID and its SHA-256 hash.
- [x] Metadata is persisted in PostgreSQL (11 / 11 backend tests pass:
      6 API + 5 unit, against PostgreSQL 16).
- [x] Re-uploading a byte-identical file gives the same hash; a
      one-byte-changed file gives a different hash.
- [x] Unauthorized (PENDING) issuer upload is rejected with 403.
- [x] Live server verified: `/health` returns connected, `/docs` returns 200.
- [ ] Blockchain registration — intentionally NOT done in Phase 2.
      That is Phase 3, where `blockchain_status` becomes ACTIVE.
