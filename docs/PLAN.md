# Phase-wise Plan — Blockchain-Based Academic Certificate Verification System

> Source of truth: `../user/files/Blockchain_Based_Academic_Certificate_Verification_Full_Notes.md`
> (referred to below as “the notes”, with section numbers).
>
> **Anti-hallucination rule for this plan:** anything the notes do not state is
> marked **NOT STATED — decision needed**, not presented as a requirement.
> Example values in the notes (e.g. `CERT-X7K29A`, `83af92...`, `0x827ab...`,
> dashboard totals 10 / 9 / 1) are examples / placeholders, not real data.

---

## 1. Brainstorm — what the notes actually say

### 1.1 Core idea (Sections 1–2)

Securely issue, store, verify, and revoke academic certificates.

- SHA-256 creates a unique digital fingerprint of each certificate file.
- Verification information goes on a **local blockchain**.
- Student details and other certificate metadata go in **PostgreSQL**.
- A verifier must be able to tell whether a certificate is
  **Valid, Modified, Revoked, or Not Found**.

### 1.2 Objectives (Section 3) — all 9 must be covered, no more added

1. Secure verification of academic certificates.
2. Detect modified / tampered certificate files.
3. Only authorized college issuers can register certificates.
4. Authorized issuers can revoke certificates.
5. Students can download and share their certificates.
6. Verifiers can verify certificates by uploading the PDF.
7. Maintain a verification history.
8. Provide QR-based certificate reference and verification.
9. Maintain certificate verification records using blockchain technology.

### 1.3 Users and responsibilities (Section 4)

| User | Responsibilities stated in the notes | Flow stated? |
|---|---|---|
| Administrator | Authorize a college/issuer; view authorized issuers; manage issuer access; prevent unauthorized users from issuing | Yes: Admin Login → Issuer Administration → Authorize Issuer → Issuer Gets Permission |
| Issuer / College | Upload or generate certificates; register certificates; view issued certificates; revoke certificates; view blockchain transaction status | Yes: Issuer Login → Dashboard → Upload Certificate → Register Certificate → Blockchain Transaction |
| Student | View certificate details; download certificate; access Certificate ID; access QR code; share the certificate reference | No flow stated |
| Verifier (employer, institution, or other person) | Upload certificate PDF; verify certificate; view verification result | No flow stated, but Section 14 calls the verification page “Public” |

### 1.4 Technology — exactly as listed (Section 5 + Final Technology Structure)

| Technology | Purpose in the notes |
|---|---|
| React | Frontend — interactive, user-friendly interface |
| Python | Backend programming — file processing and hashing |
| FastAPI | Backend API — connects frontend, database, and blockchain |
| PostgreSQL | Database — student, issuer, certificate metadata, and logs |
| Solidity | Smart contract — certificate registration and revocation rules |
| Hardhat | Local blockchain — develop and test locally |
| SHA-256 | Hashing — unique fingerprint of the certificate file |
| ethers.js | Blockchain communication — interact with the Solidity contract |
| QR Code | Certificate reference — quick access to the verification page |

Other stated facts:

- Certificate format: **PDF**.
- Real Ethereum Mainnet: **not required**. Real cryptocurrency: **not required**.
  Hardhat local blockchain: **used** (Section 12).
- Personal information and the complete certificate PDF will **not** be stored
  on the blockchain (Section 8).

### 1.5 Backend flow (Section 7)

Receive Certificate → Validate Request → Generate Certificate ID →
Calculate SHA-256 Hash → Store Certificate Metadata → Communicate with
Blockchain → Return Result to React.

### 1.6 Database records (Section 8) — only these fields are listed

- **Issuer:** Issuer ID, College Name, Wallet Address, Authorization Status
- **CertificateMetadata:** Certificate ID, Student Name, Course, Certificate File,
  Issue Date
- **VerificationLog:** Verification ID, Certificate ID, Verification Date,
  Verification Result

Note: the registration form (Section 14) also asks for **College**, which is
not listed as a separate CertificateMetadata field in Section 8. That mapping
is a decision for Phase 2, not something to assume now.

### 1.7 What goes on-chain (Section 9) — and only this

Certificate ID + SHA-256 Hash + Issuer Address + Certificate Status.

Example in the notes:

```text
Certificate ID : CERT-X7K29A
Hash           : 83af29...91bc
Issuer         : 0x72F...
Status         : ACTIVE
```

### 1.8 Smart contract operations (Section 11)

Authorize Issuer, Register Certificate, Get Certificate Record,
Revoke Certificate, Check Certificate Status.

Rule: **only an authorized issuer will be allowed to issue or revoke**
a certificate.

### 1.9 Architecture (Section 13)

Users (Admin / Issuer / Student / Verifier) → React Frontend → Python + FastAPI
Backend → PostgreSQL (metadata) **and** Solidity Smart Contract → Hardhat
Local Blockchain.

### 1.10 Frontend pages listed (Section 6) — 11 pages

Home Page, Login Page, Admin Dashboard, Issuer Dashboard,
Certificate Registration Page, Student Certificate List,
Certificate Verification Page, Revocation Page, Transaction Status,
Verification History, QR Verification Page.

Designs are given in Section 14 **only** for: Home Page, Issuer Dashboard,
Certificate Registration Page, and Public Certificate Verification Page.
The other 7 pages have no design in the notes — they need a design decision
in Phase 4 before building them.

Registration form fields (Section 14): Student Name, Course, College,
Issue Date, Certificate PDF (Choose File).

After successful registration, the notes show: Certificate ID, SHA-256,
Transaction, Status ACTIVE, and a QR Code, with the message
`CERTIFICATE REGISTERED SUCCESSFULLY`.

### 1.11 The three core flows (Sections 15–17)

**Registration:** Issuer Login → Is Issuer Authorized? (NO → Reject) →
Upload Certificate → Generate Certificate ID → Calculate SHA-256 →
Store Metadata in PostgreSQL → Call Smart Contract
(ID + Hash + Issuer + Status) → Blockchain Transaction → Generate QR Code →
Certificate Registered.

**Verification:** Upload Certificate PDF → Calculate SHA-256 Hash →
Get Blockchain Record → Record Exists? (NO → NOT FOUND) → Revoked?
(YES → REVOKED) → Compare Hash → Matches? (YES → VALID, NO → MODIFIED).

**Revocation:** Issuer Login → Select Certificate → Click Revoke →
Check Issuer Authorization → Call Smart Contract → ACTIVE → REVOKED →
Record Blockchain Transaction → Certificate Status Updated.
The record is **not deleted** from the blockchain; its status changes so the
previous ledger record/history remains available.

### 1.12 The ID-lookup rule — do not blur this (Section 18)

- **Certificate ID Search:** entering an existing ID (e.g. `CERT-X7K29A`)
  shows **Record Found**. It must **not** automatically claim an uploaded
  file is valid.
- **File Verification:** Upload PDF → SHA-256 → Compare with blockchain hash
  → Hash Matches → VALID.

In short: **ID Lookup = Record Lookup. PDF Hash Match = File Verification.**

### 1.13 Acceptance demonstration (Section 19) — exactly this

Create **10 synthetic/sample certificates** and demonstrate:

1. Register 10 certificates.
2. Upload an original certificate → VALID.
3. Modify one byte / file content and upload it → MODIFIED.
4. Revoke one certificate → REVOKED.
5. Search an unknown Certificate ID → NOT FOUND.
6. Try to issue a certificate using an unauthorized account → REJECTED.
7. Test smart-contract permissions automatically.

### 1.14 Complete project flow (Section 20)

Admin Authorizes Issuer → Issuer Uploads Certificate → FastAPI Receives
Certificate → Generate Certificate ID → Generate SHA-256 Hash →
Store Metadata in PostgreSQL → Register Through Solidity Smart Contract →
Hardhat Blockchain Records Transaction → Generate QR / Certificate Reference
→ Student Receives Certificate → Verifier Uploads Certificate →
SHA-256 Generated Again → Compare With Blockchain Record →
VALID / MODIFIED / REVOKED / NOT FOUND.

---

## 2. Brainstorm — gaps, ambiguities, and risks (NOT in the notes)

These are **not requirements**. Each one needs a decision before the phase
that depends on it, and the decision must be written down — not silently
assumed in code.

### 2.1 Decisions needed before building

1. **Login / authentication method — NOT STATED.**
   The notes show “Admin Login” and “Issuer Login” but never say how login
   works (password, wallet, or something else), who creates the Admin account,
   or how a Student gets an account to view their list.
2. **Who actually calls the smart contract — AMBIGUOUS.**
   Section 5 says ethers.js is for blockchain communication, but ethers.js is
   JavaScript, while the backend is Python + FastAPI. Section 13 shows FastAPI
   connecting to the smart contract. Decide in Phase 3: does React call the
   contract directly with ethers.js, does FastAPI call it, or both in defined
   places? Do not build both paths by accident.
3. **Certificate ID generation rule — NOT STATED.**
   Only the example `CERT-X7K29A` is given. No rule for format, randomness,
   or uniqueness checking is stated.
4. **Where the PDF file itself lives — NOT STATED.**
   Section 8 lists “Certificate File” under CertificateMetadata, but does not
   say file system vs. database storage. It only states the full PDF is not
   on the blockchain.
5. **What the QR code encodes — NOT STATED.**
   Only that it provides “quick access to the certificate verification page.”
   It is not stated whether it encodes a URL, a Certificate ID, or a hash.
6. **Student-to-certificate linking — NOT STATED.**
   No rule is given for how a student account maps to their certificates.
7. **Verifier login — NOT STATED, except the page is called “Public”.**
   Treat public verification as the working assumption to confirm in Phase 0;
   do not add a verifier login unless decided.
8. **Transaction Status and Verification History audiences — NOT STATED.**
   Both are listed as frontend pages, but the notes do not say who views them
   (Admin, Issuer, both, or public).
9. **Issuer wallet provisioning — NOT STATED.**
   Issuers have a Wallet Address, but the notes do not say where wallets come
   from (e.g. Hardhat accounts) or who supplies them.
10. **“Upload or generate certificates” — GENERATION NOT DESCRIBED.**
    The Issuer responsibilities mention generating certificates, but the
    registration page only shows uploading a PDF. Generation, if built at all,
    is out of scope until decided in Phase 0.
11. **Versions — NOT STATED.**
    No versions are given for React, Python, FastAPI, PostgreSQL, Solidity, or
    Hardhat. Choose and record them in Phase 0; do not present a version
    choice as if it came from the notes.

### 2.2 Risks to handle explicitly (derived from the notes, not new features)

- **Exact-file hashing:** Section 10 says even a slight change changes the
  hash. That also means re-saving / re-exporting an otherwise identical PDF
  will produce MODIFIED. The demo must keep byte-identical originals.
- **Local-chain state:** the project uses a local Hardhat chain only
  (Section 12). The demo run-book must cover starting the node, deploying,
  and re-deploying, so a restarted local chain does not silently invalidate
  the demo.
- **Two sources of truth:** PostgreSQL holds metadata/history, the blockchain
  holds ID + hash + issuer + status. Verification (Section 16) reads the
  blockchain record — if the two disagree, the plan must say which one the
  verification result follows, and that decision must match Section 16.
- **ID lookup vs. file verification confusion:** the UI must never label
  “Record Found” as VALID (Section 18). This is a UI wording check in Phase 5.
- **Authorization in two places:** Section 15 checks authorization before
  registration, and Section 11 enforces it in the contract. Both layers must
  be tested (see Phase 6, case 6 and 7) — passing one layer is not proof
  the other works.

### 2.3 Explicitly out of scope (per the notes)

- Real Ethereum Mainnet, real cryptocurrency (Section 12).
- Storing personal information or the full PDF on the blockchain (Section 8).
- Deleting a revoked certificate from the blockchain (Section 17).
- Any user role, page, field, or outcome not listed in Sections 3–6, 8, 11,
  and 16 — unless added by an explicit new decision in Phase 0.

---

## 3. Phase-wise plan

Phases run in order because each one depends on the previous one.
No dates are set here — no deadline was given in the notes or the request,
so do not invent one. Add dates only once you confirm a submission date.

### Phase 0 — Freeze scope and decisions (no feature code yet)

**Goal:** turn Section 2.1 into written decisions, so later phases do not
guess.

**In scope:**

- Confirm the 9 objectives, 4 roles, 11 frontend pages, 3 database records,
  5 contract operations, and 7 demo cases as the full scope.
- Decide items 1–11 in Section 2.1 and record each decision with its reason.
- Choose and record tool versions.
- Set up this repo, folder structure, and a demo run-book outline.

**Deliverable:** a short `docs/DECISIONS.md` (one line per decision) +
this plan, agreed before Phase 1.

**Exit criteria:**

- [ ] Every item in Section 2.1 has a written decision or is explicitly
  deferred to a named later phase.
- [ ] No feature outside Sections 3–6, 8, 11, and 16 is in the build list.

### Phase 1 — Blockchain: Solidity contract + Hardhat local chain

**Goal:** the tamper-resistant record from Sections 9 and 11, on a local
chain only.

**In scope (notes Sections 9, 11, 12):**

- Contract operations: Authorize Issuer, Register Certificate,
  Get Certificate Record, Revoke Certificate, Check Certificate Status.
- On-chain data only: Certificate ID, SHA-256 Hash, Issuer Address,
  Certificate Status (ACTIVE / REVOKED).
- Rule: only an authorized issuer can issue or revoke.
- Revocation changes status ACTIVE → REVOKED; it does not delete the record.
- Hardhat local deployment and test scripts. No mainnet, no real crypto.

**Out of scope:** frontend, backend API, database, PDF handling.

**Deliverable:** `blockchain/` — contract, Hardhat config, deploy script,
contract tests.

**Exit criteria:**

- [ ] An unauthorized account cannot register or revoke (contract test).
- [ ] An authorized issuer can register, read back, and revoke a certificate,
  and status reads back as REVOKED afterwards.
- [ ] No personal data and no PDF bytes are stored on-chain.

### Phase 2 — Backend + database: FastAPI + PostgreSQL

**Goal:** the Section 7 backend flow and the Section 8 database records,
without blockchain wiring yet (that is Phase 3).

**In scope (notes Sections 7–8, 10):**

- API flow: Receive Certificate → Validate Request → Generate Certificate ID
  → Calculate SHA-256 Hash → Store Certificate Metadata → Return Result.
- Tables exactly as listed in Section 8: Issuer, CertificateMetadata,
  VerificationLog, with the fields listed there.
- SHA-256 over the exact uploaded PDF bytes.
- Certificate ID generation following the Phase 0 decision.
- PDF storage location following the Phase 0 decision.

**Out of scope:** contract calls (Phase 3), any frontend page.

**Deliverable:** `backend/` (FastAPI app) + database schema / migrations.

**Exit criteria:**

- [ ] Uploading a PDF returns a Certificate ID and its SHA-256 hash.
- [ ] Metadata and (later) verification attempts are persisted in PostgreSQL.
- [ ] Re-uploading a byte-identical file gives the same hash; a changed file
  gives a different hash.

### Phase 3 — Connect backend ↔ blockchain

**Goal:** resolve the Section 2.1, item 2 ambiguity and wire the full
registration path from Section 15.

**In scope (notes Sections 5, 9, 13, 15):**

- One defined blockchain-calling path (per the Phase 0 / Phase 3 decision),
  using ethers.js where the notes assign it, without duplicating the path.
- Registration end-to-end: authorization check → metadata in PostgreSQL →
  contract call (ID + Hash + Issuer + Status) → blockchain transaction
  returned to the caller.
- Transaction reference (the notes show an example `0x827ab...`) available
  for the Transaction Status view.

**Out of scope:** frontend pages (Phase 4).

**Deliverable:** working backend-to-chain registration and status reads,
documented in the repo.

**Exit criteria:**

- [ ] A registered certificate can be read back from the contract by ID,
  with matching hash, issuer, and ACTIVE status.
- [ ] An unauthorized issuer is rejected before a contract write (Section 15)
  and also by the contract (Section 11).
- [ ] A failed contract write does not leave a misleading “registered”
  result — the failure path is defined and recorded.

### Phase 4 — Frontend: React pages

**Goal:** all 11 pages listed in Section 6, using the Section 14 designs
where they exist.

**In scope (notes Sections 6, 14):**

- Home Page, Login Page, Admin Dashboard, Issuer Dashboard,
  Certificate Registration Page, Student Certificate List,
  Certificate Verification Page, Revocation Page, Transaction Status,
  Verification History, QR Verification Page.
- Section 14 designs for Home, Issuer Dashboard, Registration, and Public
  Verification — including the registration form fields (Student Name,
  Course, College, Issue Date, Certificate PDF) and the post-registration
  display (Certificate ID, SHA-256, Transaction, Status ACTIVE, QR Code).
- Issuer Dashboard contents as drawn: total / active / revoked counts,
  Register Certificate action, Recent Certificates, and the
  Dashboard / Register Certificate / Certificates / Revoke / Logout navigation.

**Note on the dashboard numbers:** the Section 14 drawing shows
Total 10, Active 9, Revoked 1. Those are drawing examples, not a requirement
that real data must equal 10 / 9 / 1.

**Deliverable:** `frontend/` (React app) wired to the Phase 2–3 backend.

**Exit criteria:**

- [ ] Each of the 11 pages exists and is reachable from the navigation the
  notes describe.
- [ ] Admin can view authorized issuers and authorize an issuer
  (Section 4A).
- [ ] Issuer can view issued certificates and transaction status
  (Section 4B).
- [ ] Student can view details, download, and access Certificate ID and QR
  code (Section 4C).

### Phase 5 — End-to-end flows: verification, revocation, QR, ID lookup

**Goal:** the three flows in Sections 15–17 plus the Section 18 rule,
working end-to-end, not just as separate pages.

**In scope:**

- **Registration flow (Section 15)** — full path, ending in QR generation
  and “Certificate Registered”.
- **Verification flow (Section 16)** — Upload PDF → SHA-256 → blockchain
  record → NOT FOUND / REVOKED / VALID / MODIFIED, exactly in that order.
  Every verification is recorded in VerificationLog (Section 8, Objective 7).
- **Revocation flow (Section 17)** — Issuer Login → Select Certificate →
  Click Revoke → Authorization check → Contract call → ACTIVE → REVOKED →
  transaction recorded → status updated.
- **QR verification (Objectives 8, Section 6)** — QR gives quick access to
  the verification page, encoding whatever Phase 0 decided.
- **ID lookup (Section 18)** — an existing ID shows “Record Found” only;
  it never shows VALID on its own. Only a PDF hash match shows VALID.

**Deliverable:** integrated app with all flows, plus a flow checklist.

**Exit criteria:**

- [ ] Each of the four verification outcomes can be produced on demand
  (see Phase 6 for the exact demo cases).
- [ ] ID search and PDF verification show different, correctly worded results.
- [ ] A revoked certificate verifies as REVOKED, not as MODIFIED or VALID,
  even when the uploaded file is byte-identical to the original.
- [ ] Every verification attempt appears in Verification History /
  VerificationLog.

### Phase 6 — Testing and acceptance demonstration

**Goal:** run Section 19 exactly, with nothing added or skipped.

**In scope (Section 19):**

- Create 10 synthetic/sample certificates.
- Demonstrate, in order:
  1. Register 10 certificates.
  2. Upload an original certificate → VALID.
  3. Modify one byte / file content and upload it → MODIFIED.
  4. Revoke one certificate → REVOKED.
  5. Search an unknown Certificate ID → NOT FOUND.
  6. Try to issue a certificate using an unauthorized account → REJECTED.
  7. Test smart-contract permissions automatically.

**Deliverable:** demo script / checklist, the 10 synthetic certificates
(or their generation steps, if they are generated), and a demo result log.

**Exit criteria:**

- [ ] All 7 cases pass and are recorded with the actual result shown.
- [ ] Case 3 uses a genuinely modified file (one byte / content change),
  not a different certificate.
- [ ] Case 5 uses an ID that was never registered.
- [ ] Case 6 is attempted through the real path (not a mocked rejection),
  and case 7 is an automated contract test, not a manual claim.

### Phase 7 — Documentation, notebook diagrams, and submission pack

**Goal:** the material a college project is actually marked on, drawn from
the notes — not invented after the build.

**In scope (notes Sections 13–14, 20):**

- Architecture diagram (Section 13).
- Frontend designs (Section 14).
- Registration, verification, revocation, and complete flows
  (Sections 15, 17, 20).
- Final Technology Structure summary (Section: Final Technology Structure).
- Demo evidence from Phase 6 and the decisions log from Phase 0.
- A README that states scope, tech, how to run locally, and how to run
  the demo — all consistent with the phases above.

**Out of scope:** claiming mainnet deployment, production hosting, or any
feature not built in Phases 1–6.

**Deliverable:** submission-ready docs in `docs/` + README.

**Exit criteria:**

- [ ] Every diagram in the notes has a matching diagram in the submission.
- [ ] README run steps reproduce the Phase 6 demo from a clean local start.
- [ ] No claim in the docs contradicts Sections 8, 9, 12, 17, or 18.

---

## 4. Traceability — phase → notes sections → objectives

| Phase | Notes sections | Objectives (Section 3) |
|---|---|---|
| 0 — Decisions | Whole notes, esp. Sections 2.1 gaps above | All (scope freeze) |
| 1 — Blockchain | 9, 11, 12 | 3, 4, 9 |
| 2 — Backend + DB | 7, 8, 10 | 2, 7, 9 |
| 3 — Backend ↔ chain | 5, 9, 13, 15 | 3, 9 |
| 4 — Frontend | 6, 14 | 5, 6, 8 |
| 5 — Flows | 15, 16, 17, 18 | 1, 2, 4, 5, 6, 7, 8 |
| 6 — Demo | 19 | 1, 2, 3, 4 |
| 7 — Docs | 13, 14, 20, Final Structure | All |

## 5. Repo structure (this repo)

```text
certificate-verification-blockchain/
├── README.md
├── docs/
│   ├── PLAN.md            # this file
│   └── DECISIONS.md       # to be written in Phase 0
├── frontend/              # React — Phase 4
├── backend/               # Python + FastAPI — Phases 2–3
└── blockchain/            # Solidity + Hardhat — Phase 1
```

**Status right now (updated 2026-10-25):** Phase 0 done — decisions confirmed
in `docs/DECISIONS.md`. Phase 1 done — contract, deploy script, and 11 tests
in `blockchain/` (see `blockchain/README.md`). Phase 2 done — FastAPI +
PostgreSQL backend in `backend/` (see `backend/README.md`; 11 tests pass
against PostgreSQL 16). Phase 3 done — backend ↔ blockchain: read-only
web3 verification + confirm endpoints in `backend/`, ethers.js submit
script in `blockchain/`, 15 pytest tests + live Hardhat/backend
end-to-end check pass. Phase 4 done — React frontend in `frontend/`
(all 11 pages, Vite build passes) + backend login/token auth
(17 pytest tests + Phase 3 live check still pass). Full file
verification (VALID / MODIFIED / REVOKED + logging) is done in
Phase 5 (POST /verify, 24 pytest tests + live check pass). Phase 6
done (demo/run_demo.py, all 7 Section 19 cases pass, evidence in
demo/DEMO_RESULT.md). Phase 7 done (submission/ pack, demo
re-run from a clean start passes). Project complete — only the
submission deadline is TBD.
