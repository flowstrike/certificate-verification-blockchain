# Blockchain-Based Academic Certificate Verification System

College project — phase-wise plan first, code second.

**Scope, exactly as in the project notes:**

- Securely issue, store, verify, and revoke academic certificates.
- SHA-256 fingerprint of each certificate PDF.
- Verification info on a local blockchain (Hardhat); student details and
  certificate metadata in PostgreSQL.
- Verification outcomes: **Valid, Modified, Revoked, or Not Found**.
- ID lookup shows **Record Found** only — it is not file verification.
  Only a PDF hash match shows **VALID**.
- No real Ethereum Mainnet, no real cryptocurrency, no personal data or
  full PDF on the blockchain, and revoked records are never deleted —
  their status changes from ACTIVE to REVOKED.

**Tech (from the notes):** React, Python + FastAPI, PostgreSQL, Solidity,
Hardhat, SHA-256, ethers.js, QR Code. Certificate format: PDF.

**Start here:** [docs/PLAN.md](docs/PLAN.md) — brainstorm, gaps that still
need decisions, and the 8 phases (Phase 0 to Phase 7).

**Status:** Phase 0 done (decisions confirmed in `docs/DECISIONS.md`).
Phase 1 done: Solidity contract + Hardhat tests in `blockchain/`
(11 / 11 tests pass). Phase 2 done: FastAPI + PostgreSQL backend in
`backend/` (11 / 11 tests pass against PostgreSQL 16). Phase 3 done:
backend ↔ blockchain in `backend/` + ethers.js submit script in
`blockchain/` (15 pytest tests + live Hardhat + backend end-to-end
check pass; backend verifies on-chain before marking ACTIVE/REVOKED).
Phase 4 done: React frontend in `frontend/` (all 11 pages, Vite build
passes) + backend login/token auth in `backend/`. Phase 5 done:
POST /verify (VALID / MODIFIED / REVOKED / NOT_FOUND + history
logging), ID lookup kept separate from file verification, QR = URL +
ID (lookup only, not VALID by itself); 24 pytest tests + Phase 5
live check pass. Phase 6 done: `demo/run_demo.py` creates 10 synthetic
certificates and proves all 7 Section 19 cases (10 registered, VALID,
MODIFIED, REVOKED, NOT FOUND, unauthorized REJECTED, 11 contract tests
passing) — evidence in `demo/DEMO_RESULT.md`. Phase 7 done:
submission pack in `submission/` (main document, architecture
diagram, clean-start runbook, Phase 0 decisions log), verified by
re-running the demo from a clean start (all cases pass, new IDs as
expected). Project complete — only the submission deadline is TBD.
