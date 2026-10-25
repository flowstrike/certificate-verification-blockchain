const hre = require("hardhat");

// Deploy to the local Hardhat network only.
// Usage:
//   npx hardhat node            (terminal 1: local chain)
//   npx hardhat run scripts/deploy.js --network localhost   (terminal 2)
async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with admin/deployer account:", deployer.address);

  const CertificateVerification = await hre.ethers.getContractFactory(
    "CertificateVerification"
  );
  const contract = await CertificateVerification.deploy();
  await contract.waitForDeployment();

  console.log("CertificateVerification deployed to:", await contract.getAddress());
  console.log("Admin (deployer):", await contract.admin());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
