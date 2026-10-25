# Submission Pack — README

This folder is the submission pack for the Blockchain-Based Academic
Certificate Verification System (Phase 7). It is self-contained: a
reader with the repo can follow it without needing the rest of the
conversation that built the project.

## Files in this pack

- **`SUBMISSION.md`** — the main submission document: introduction,
  objectives with implementation mapping, users, technologies with
  exact versions, architecture, database, blockchain, smart contract,
  frontend (including the four designs from the notes, Section 14),
  registration / verification / revocation / complete flows,
  ID-lookup-vs-file-verification rule, testing and acceptance
  demonstration, honest limitations, future work (proposals only,
  not built), project structure, and sources.
- **`architecture.svg`** — system architecture diagram (notes,
  Section 13, with the Phase 0 backend-verifies / React-sends-tx
  split shown explicitly). The same diagram is also in
  `SUBMISSION.md` as a Mermaid flowchart.
- **`RUNBOOK.md`** — clean local start: PostgreSQL, Hardhat node +
  deploy, backend, frontend, demo script, tests, and troubleshooting.
- **`DECISIONS.md`** — Phase 0 decisions log, copied from
  `docs/DECISIONS.md`. Anything the notes do not state is marked as
  a decision here, never as a notes requirement.

## Evidence that lives outside this folder (referenced, not copied)

- `demo/DEMO_RESULT.md` — the latest Section 19 demo run: 10
  certificates, their IDs, hashes, transaction hashes, and all 7
  cases plus 2 extras. IDs and hashes change on every run.
- `demo/certificates/` — the 10 synthetic sample PDFs (labelled
  synthetic inside each PDF) plus the 1-byte-modified PDF.
- `blockchain/test/`, `backend/tests/` — the automated tests
  (11 Hardhat, 24 pytest).

## Before submitting

Fill in the placeholders marked `[to fill in]` in `SUBMISSION.md`:
student name, roll number, college, guide name, and submission date.
No personal details have been invented in this pack. If your college
requires a specific format (for example a PDF or a printed report),
convert `SUBMISSION.md` to that format and check that the diagram
(`architecture.svg`) and the demo evidence (`demo/DEMO_RESULT.md`)
are included with it.
