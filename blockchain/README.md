# Blockchain — Solidity + Hardhat (Phase 1: DONE)

Contract: `contracts/CertificateVerification.sol`

Operations, from the notes Section 11:

- Authorize Issuer (admin only)
- Register Certificate (authorized issuer only)
- Get Certificate Record
- Revoke Certificate (authorized issuer only)
- Check Certificate Status

On-chain data only, from the notes Section 9: Certificate ID, SHA-256 Hash,
Issuer Address, Certificate Status (None / Active / Revoked).

Local Hardhat chain only — no mainnet, no real cryptocurrency (Section 12).
Personal data and PDFs are never stored on-chain (Section 8).
Revocation changes status Active → Revoked and never deletes the record
(Section 17).

Note: the notes require only an *authorized* issuer to register/revoke.
They do not state an extra “original issuer only” rule for revocation,
so none was added.

## Versions recorded at install (Phase 0, decision 11)

- Hardhat 2.29.1, `@nomicfoundation/hardhat-toolbox` 5.0.0
- Solidity 0.8.28
- Node v24.22.1 (on this machine)

## Run

```bash
cd blockchain
npm install
npx hardhat compile
npx hardhat test
```

Local deploy (two terminals):

```bash
npx hardhat node
npx hardhat run scripts/deploy.js --network localhost
```

The deployed address changes on a fresh local node — it is not permanent.
Record the address from the deploy output when you need it in Phase 3.

## Phase 3 — ethers.js submit script

`scripts/submit_tx.js` is the write path React + ethers.js will use in
Phase 4, proven now without the UI. It runs under Hardhat (no private
keys in the repo) and always prints a JSON object as its last line:

```bash
MODE=authorize CONTRACT_ADDRESS=0x... npx hardhat run scripts/submit_tx.js --network localhost
MODE=register  CONTRACT_ADDRESS=0x... CERT_ID=CERT-XXXXXX CERT_HASH=<64 hex, no 0x> \
  npx hardhat run scripts/submit_tx.js --network localhost
MODE=revoke    CONTRACT_ADDRESS=0x... CERT_ID=CERT-XXXXXX \
  npx hardhat run scripts/submit_tx.js --network localhost
MODE=read      CONTRACT_ADDRESS=0x... CERT_ID=CERT-XXXXXX \
  npx hardhat run scripts/submit_tx.js --network localhost
```

Signers: [0] admin, [1] authorised issuer, [2] unauthorised (demo).

## Phase 1 exit criteria — all verified 2026-10-25

- [x] An unauthorized account cannot register or revoke (contract tests).
- [x] An authorized issuer can register, read back, and revoke a certificate,
      and status reads back as Revoked afterwards.
- [x] No personal data and no PDF bytes are stored on-chain — the contract
      only stores ID, a bytes32 hash, issuer address, and status.
- [x] 11 / 11 Hardhat tests pass, including unknown-ID (None) and
      duplicate-registration cases.
- [x] Deploy script verified against a local Hardhat node.
