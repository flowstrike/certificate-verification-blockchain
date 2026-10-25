# Demo Result — Blockchain-Based Academic Certificate Verification

Run at (UTC): 2026-10-25T09:53:53.683898+00:00
Contract address (local Hardhat, this run only): 0x5FbDB2315678afecb367f032d93F642f64180aa3
Issuer wallet (Hardhat account 1): 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
Issuer login (demo): demo-issuer@demo.local / demo123
Admin login (demo): admin@demo.local / admin123
Backend (this run): http://127.0.0.1:8001 — database: certificate_demo

Overall: ALL CASES PASS (9/9 pass)

## Registered certificates (10 synthetic samples)

| # | Student | Course | Certificate ID | SHA-256 (first 16) | Status | Transaction (first 16) |
|---|---|---|---|---|---|---|
| 1 | Aarav Sharma | BSc Computer Science | CERT-I3ZZDD | 5abf8cd5db13d2e6… | ACTIVE | 0x346ec2503e2a9c… |
| 2 | Priya Patel | BCom | CERT-QLIUET | d81ef46f2b66914d… | REVOKED | 0xdb1ea971408a16… |
| 3 | Rohan Verma | BSc Mathematics | CERT-JLSPQH | 9081cd6109fbe772… | ACTIVE | 0x783199a8edce97… |
| 4 | Sneha Kulkarni | BA English | CERT-2Q4ZD1 | 36946b118819c56a… | ACTIVE | 0x1c40458fa4a79b… |
| 5 | Arjun Mehta | BTech Information Technology | CERT-77089F | c13b37f83c7f3875… | ACTIVE | 0x40f71233d3f5bf… |
| 6 | Kavya Nair | BSc Physics | CERT-WPA8V9 | 3acce7779761aae0… | ACTIVE | 0x0dc1bf39a3d9df… |
| 7 | Vikram Singh | BBA | CERT-RGQHIY | 4d33cc35651d6329… | ACTIVE | 0x819fa4e8463e98… |
| 8 | Ananya Iyer | BSc Chemistry | CERT-6QKDAR | d9dd6005fd0beac4… | ACTIVE | 0x76d70ea4d2e23a… |
| 9 | Aditya Joshi | BCom Accounting | CERT-CS0X82 | 1326811d58e27156… | ACTIVE | 0x93931a5dac67c5… |
| 10 | Meera Desai | BA Economics | CERT-4ZEZXJ | 8c98be1ed0abc73d… | ACTIVE | 0x31faae2590bfe1… |

## Cases (notes, Section 19, in order)

### Case 1: Register 10 certificates — PASS
- Expected: 10 ACTIVE
- Actual: 10 ACTIVE
- Detail: IDs: CERT-I3ZZDD, CERT-QLIUET, CERT-JLSPQH, CERT-2Q4ZD1, CERT-77089F, CERT-WPA8V9, CERT-RGQHIY, CERT-6QKDAR, CERT-CS0X82, CERT-4ZEZXJ

### Case 2: Original certificate — PASS
- Expected: VALID
- Actual: VALID
- Detail: Certificate CERT-I3ZZDD, no ID supplied (fingerprint lookup)

### Case 3: Modified certificate (1 byte, with ID) — PASS
- Expected: MODIFIED
- Actual: MODIFIED
- Detail: Byte 1208 changed (65 -> 88), Certificate CERT-I3ZZDD. Without an ID this would be NOT_FOUND (Phase 5 finding).

### Case 4: Revoked certificate — PASS
- Expected: REVOKED
- Actual: REVOKED
- Detail: Certificate CERT-QLIUET, original file, after revocation

### Case 5: Unknown Certificate ID — PASS
- Expected: NOT FOUND (NOT_FOUND)
- Actual: NOT_FOUND
- Detail: GET /certificates/CERT-UNKNOWN -> 404; /verify CERT-UNKNOWN -> NOT_FOUND. CERT-UNKNOWN was never registered.

### Case 6: Unauthorized issue attempt — PASS
- Expected: REJECTED
- Actual: backend=403, contract_rejected=True
- Detail: Backend upload by PENDING issuer -> 403; contract register by unauthorised wallet (0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC) -> rejected; main issuer still has 10 certificates.

### Case 7: Smart-contract permissions (automated tests) — PASS
- Expected: 11 passing, 0 failing
- Actual: 11 passing, 0 failing
- Detail: npx hardhat test in blockchain/ (Phase 1 tests, including unauthorised register/revoke).

### Extra: QR link (verify?id=...) opens the record — PASS
- Expected: Record Found
- Actual: Record Found
- Detail: Simulates scanning the QR code for CERT-I3ZZDD.

### Extra: Verification history contains all four results — PASS
- Expected: VALID, MODIFIED, REVOKED, NOT_FOUND
- Actual: MODIFIED, NOT_FOUND, REVOKED, VALID
- Detail: 4 log rows in this demo run.

## Notes for the presenter

- Certificate IDs and transaction hashes in this file are from this run only. Re-running the demo generates new IDs (they are random) and new transaction hashes (fresh local chain).
- Case 3 supplies the Certificate ID, because a modified file's new fingerprint alone cannot identify its original (Phase 5 finding).
- Case 6 was attempted through real paths, not mocked: a real backend 403 for a PENDING issuer, and a real contract revert for an unauthorised wallet. No certificate was created by either attempt.
- All 10 PDFs are synthetic samples, labelled as such inside each PDF, in demo/certificates/. No real student data is used.
- To show the same certificates in the frontend afterwards, re-run with --keep-servers, then open the frontend (see demo/README.md).
