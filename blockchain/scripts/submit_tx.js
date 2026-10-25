const hre = require("hardhat");

// Phase 3: the ethers.js write path, before the React UI exists (Phase 4).
// This script is exactly what React + ethers.js will do in Phase 4:
// the issuer's wallet sends register / revoke transactions to the contract.
// It runs under Hardhat so it can use Hardhat's local test accounts
// without ever handling a private key in this repo.
//
// Usage (local Hardhat node running in another terminal):
//   npx hardhat node
//   npx hardhat run scripts/deploy.js --network localhost
//   # then, with CONTRACT_ADDRESS set to the deployed address:
//   MODE=authorize CONTRACT_ADDRESS=0x... npx hardhat run scripts/submit_tx.js --network localhost
//   MODE=register  CONTRACT_ADDRESS=0x... CERT_ID=CERT-XXXXXX CERT_HASH=<64 hex chars, no 0x> \
//       npx hardhat run scripts/submit_tx.js --network localhost
//   MODE=revoke    CONTRACT_ADDRESS=0x... CERT_ID=CERT-XXXXXX \
//       npx hardhat run scripts/submit_tx.js --network localhost
//   MODE=read      CONTRACT_ADDRESS=0x... CERT_ID=CERT-XXXXXX \
//       npx hardhat run scripts/submit_tx.js --network localhost
//   MODE=register_unauthorized  CONTRACT_ADDRESS=0x... CERT_ID=CERT-XXXXXX CERT_HASH=<64 hex> \
//       npx hardhat run scripts/submit_tx.js --network localhost
//       (Phase 6, case 6: signers[2] is unauthorised, so the contract
//       must reject this. The script catches the revert and prints a
//       JSON {rejected: true} object instead of failing, so a demo
//       script can record REJECTED as a passing case.)
//
// Signers on a Hardhat local node (confirmed Phase 0 decision 9):
//   signers[0] = admin / deployer, signers[1] = authorised issuer,
//   signers[2] = unauthorised account (for the REJECTED demo case).
// The last line printed is always a JSON object, so scripts (and the
// Phase 3 live check) can parse it reliably.

async function main() {
  const mode = process.env.MODE;
  const contractAddress = process.env.CONTRACT_ADDRESS;
  const certId = process.env.CERT_ID;
  const certHash = process.env.CERT_HASH;
  if (!contractAddress) throw new Error("CONTRACT_ADDRESS is not set");
  if (!["authorize", "register", "revoke", "read", "register_unauthorized"].includes(mode)) {
    throw new Error(`Unknown MODE: ${mode}`);
  }

  const [admin, issuer, unauthorized] = await hre.ethers.getSigners();
  const contract = await hre.ethers.getContractAt(
    "CertificateVerification",
    contractAddress
  );

  if (mode === "authorize") {
    const tx = await contract.connect(admin).authorizeIssuer(issuer.address);
    const receipt = await tx.wait();
    console.log(JSON.stringify({ tx_hash: tx.hash, status: receipt.status, issuer: issuer.address }));
    return;
  }

  if (!certId) throw new Error("CERT_ID is not set");

  if (mode === "read") {
    const [hash, issuerAddress, status] = await contract.getCertificateRecord(certId);
    const names = ["NOT_FOUND", "ACTIVE", "REVOKED"];
    console.log(JSON.stringify({
      certificate_id: certId,
      hash,
      issuer: issuerAddress,
      status: names[status] ?? "UNKNOWN",
    }));
    return;
  }

  if (mode === "register_unauthorized") {
    if (!certHash || !/^[0-9a-fA-F]{64}$/.test(certHash)) {
      throw new Error("CERT_HASH must be 64 hex characters (SHA-256, no 0x prefix)");
    }
    try {
      const tx = await contract
        .connect(unauthorized)
        .registerCertificate(certId, "0x" + certHash);
      await tx.wait();
      // If we reach here, the contract failed to enforce authorization.
      console.log(JSON.stringify({ rejected: false, signer: unauthorized.address, certificate_id: certId }));
    } catch (err) {
      console.log(JSON.stringify({ rejected: true, signer: unauthorized.address, certificate_id: certId, reason: String(err.message).slice(0, 200) }));
    }
    return;
  }

  if (mode === "register") {
    if (!certHash || !/^[0-9a-fA-F]{64}$/.test(certHash)) {
      throw new Error("CERT_HASH must be 64 hex characters (SHA-256, no 0x prefix)");
    }
    const tx = await contract
      .connect(issuer)
      .registerCertificate(certId, "0x" + certHash);
    const receipt = await tx.wait();
    console.log(JSON.stringify({ tx_hash: tx.hash, status: receipt.status, certificate_id: certId }));
    return;
  }

  // revoke
  const tx = await contract.connect(issuer).revokeCertificate(certId);
  const receipt = await tx.wait();
  console.log(JSON.stringify({ tx_hash: tx.hash, status: receipt.status, certificate_id: certId }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
