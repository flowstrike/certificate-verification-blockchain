# Phase 0 Decisions — CONFIRMED 2026-10-25

Status: Phase 0 confirmed by the user on 2026-10-25 (“Yes, use these proposed
decisions and start Phase 1”), except item 12 (deadline), which is still TBD.
Student access follows the recommended option in 1b (ID / QR access, no
student password). The notes themselves do not state these points — see
`PLAN.md` Section 2.1. “Proposed decision” below now means the confirmed
decision, unless marked TBD.

## Proposed decisions

| # | Question (not stated in the notes) | Proposed decision | Why |
|---|---|---|---|
| 1 | How do Admin / Issuer log in? | Email + password login. One seeded demo Admin account; Admin authorises issuers, which activates their Issuer login. No public signup. | Matches the notes' Admin Login / Issuer Login flows, without inventing a signup system. |
| 1b | How does a Student access certificates? | **Needs your pick — see below.** Recommended: ID / QR access, no student password. Student enters a Certificate ID (or scans QR) to view, download, and share that certificate. | Covers every Student responsibility listed in the notes (view, download, ID, QR, share) with the least new machinery. Alternative: email/password student accounts — more work, not described in the notes. |
| 2 | Who calls the smart contract? | Split, with one owner per step: FastAPI validates the request, generates the ID, hashes the PDF, and stores metadata first. React + ethers.js then sends the register / revoke transaction, and the transaction hash is recorded back in the backend. Reads (status / record lookup) go through the backend. | Keeps ethers.js in the role the notes give it, keeps Python/FastAPI in charge of hashing and metadata, and avoids two different write paths. |
| 3 | Certificate ID format? | `CERT-` + 6 uppercase letters/digits (e.g. the notes' example format `CERT-X7K29A`), checked for uniqueness in PostgreSQL before use. | Follows the only example in the notes; the uniqueness check is the new, proposed part. |
| 4 | Where is the PDF file itself stored? | On disk in a backend uploads folder, with its path referenced in the CertificateMetadata “Certificate File” field. Served back for student download. Not in the database as a blob, and never on the blockchain. | Simplest local-demo option that respects “full PDF not on the blockchain”. |
| 5 | What does the QR code encode? | The verification-page URL with the Certificate ID, e.g. verification page + `?id=CERT-...`. Scanning it opens ID lookup (“Record Found”), it does **not** by itself prove a file is valid. | Keeps the notes' Section 18 rule intact: ID lookup ≠ file verification. |
| 6 | How does a student account map to certificates? | Same as 1b: no student account mapping in the proposed default — a certificate is found by its ID / QR. If you pick student passwords instead, mapping is by student login at registration time. | Avoids inventing an account system the notes never describe. |
| 7 | Is verifier access fully public? | Yes — proposed as confirmed. No verifier login. | The notes call it the “Public Certificate Verification Page”. |
| 8 | Who views Transaction Status and Verification History? | Issuer (their own certificates) and Admin (all). Not public. | These are listed as frontend pages but no audience is stated; issuer/admin is the smallest sensible audience. |
| 9 | Where do issuer wallets come from? | Hardhat local accounts for the demo: account 0 = deployer/Admin, account 1 = authorised issuer, account 2 = unauthorised account used for the REJECTED demo case. | Fits “Hardhat local blockchain, no real cryptocurrency” and gives Phase 6 a real unauthorised account to test with. |
| 10 | Is certificate generation in scope, or upload-only? | Upload-only. Generation is out of scope unless you add it. | The notes describe upload in detail; generation appears in one line only, with no method given. |
| 11 | Tool versions? | Record exact versions at install time in each folder (Phase 1: Hardhat + Solidity 0.8.x; Phase 2: Python/FastAPI; Phase 4: React). Already checked on this machine: Node v24.22.1, npm 10.9.4, Python 3.12.3, git 2.43.0. PostgreSQL client (`psql`) is **not** installed here yet — PostgreSQL setup (local install vs Docker) is a Phase 2 task, not a blocker for Phase 1. | No versions are stated in the notes, so versions must be recorded from the actual installs, not guessed now. |
| 12 | Submission deadline / demo date? | TBD — please tell me, so phases can be ordered against it. | No date was given in the notes or your messages. |

## What Phase 0 still needs from you

1. Confirm the proposed decisions above, or say which ones to change.
2. Pick 1b: ID/QR access for students (recommended) vs student email/password accounts.
3. Give a submission/demo date, if you have one.

Once you confirm, Phase 0 is done and Phase 1 (Solidity + Hardhat) can start
without guessing — its only dependencies are decisions 9 and 11, both
proposed above.
