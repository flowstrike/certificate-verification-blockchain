const { expect } = require("chai");
const { ethers } = require("hardhat");

// Phase 1 tests, plus the automated smart-contract permission tests
// required by the notes, Section 19, case 7.
// Status enum in the contract: 0 = None (not found), 1 = Active, 2 = Revoked.
// The test hash below is a placeholder bytes32 value. In the real system
// (Phase 2) the backend passes the SHA-256 of the exact PDF bytes; the
// contract stores whatever 32 bytes it is given and never sees the PDF.

describe("CertificateVerification", function () {
  let contract;
  let admin;
  let issuer;
  let unauthorized;
  const certId = "CERT-X7K29A";
  // A fixed 32-byte value, used only as test data.
  const certHash = ethers.keccak256(ethers.toUtf8Bytes("sample-certificate-1"));

  beforeEach(async function () {
    [admin, issuer, unauthorized] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateVerification");
    contract = await Factory.deploy();
    await contract.waitForDeployment();
  });

  it("deployer is the admin", async function () {
    expect(await contract.admin()).to.equal(admin.address);
  });

  it("admin can authorize an issuer", async function () {
    await contract.authorizeIssuer(issuer.address);
    expect(await contract.authorizedIssuers(issuer.address)).to.equal(true);
  });

  it("non-admin cannot authorize an issuer", async function () {
    await expect(
      contract.connect(unauthorized).authorizeIssuer(issuer.address)
    ).to.be.revertedWith("Only admin");
  });

  it("authorized issuer can register, and the record reads back correctly", async function () {
    await contract.authorizeIssuer(issuer.address);
    await contract.connect(issuer).registerCertificate(certId, certHash);

    const [hash, issuerAddress, status] = await contract.getCertificateRecord(
      certId
    );
    expect(hash).to.equal(certHash);
    expect(issuerAddress).to.equal(issuer.address);
    expect(status).to.equal(1); // Active
    expect(await contract.checkCertificateStatus(certId)).to.equal(1);
  });

  it("unauthorized account cannot register a certificate (REJECTED)", async function () {
    await expect(
      contract.connect(unauthorized).registerCertificate(certId, certHash)
    ).to.be.revertedWith("Only authorized issuer");
    // And no record was created.
    expect(await contract.checkCertificateStatus(certId)).to.equal(0); // None
  });

  it("the same Certificate ID cannot be registered twice", async function () {
    await contract.authorizeIssuer(issuer.address);
    await contract.connect(issuer).registerCertificate(certId, certHash);
    await expect(
      contract.connect(issuer).registerCertificate(certId, certHash)
    ).to.be.revertedWith("Certificate already exists");
  });

  it("registering with an empty hash is rejected", async function () {
    await contract.authorizeIssuer(issuer.address);
    await expect(
      contract.connect(issuer).registerCertificate(certId, ethers.ZeroHash)
    ).to.be.revertedWith("Empty certificate hash");
  });

  it("authorized issuer can revoke: status becomes Revoked, record is not deleted", async function () {
    await contract.authorizeIssuer(issuer.address);
    await contract.connect(issuer).registerCertificate(certId, certHash);
    await contract.connect(issuer).revokeCertificate(certId);

    expect(await contract.checkCertificateStatus(certId)).to.equal(2); // Revoked
    const [hash, issuerAddress, status] = await contract.getCertificateRecord(
      certId
    );
    expect(hash).to.equal(certHash);
    expect(issuerAddress).to.equal(issuer.address);
    expect(status).to.equal(2);
  });

  it("unauthorized account cannot revoke a certificate", async function () {
    await contract.authorizeIssuer(issuer.address);
    await contract.connect(issuer).registerCertificate(certId, certHash);
    await expect(
      contract.connect(unauthorized).revokeCertificate(certId)
    ).to.be.revertedWith("Only authorized issuer");
    expect(await contract.checkCertificateStatus(certId)).to.equal(1); // still Active
  });

  it("a revoked certificate cannot be revoked again, and an unknown ID cannot be revoked", async function () {
    await contract.authorizeIssuer(issuer.address);
    await contract.connect(issuer).registerCertificate(certId, certHash);
    await contract.connect(issuer).revokeCertificate(certId);
    await expect(
      contract.connect(issuer).revokeCertificate(certId)
    ).to.be.revertedWith("Certificate not active");
    await expect(
      contract.connect(issuer).revokeCertificate("CERT-UNKNOWN")
    ).to.be.revertedWith("Certificate not active");
  });

  it("an unknown Certificate ID returns no record (NOT FOUND)", async function () {
    const [hash, issuerAddress, status] = await contract.getCertificateRecord(
      "CERT-UNKNOWN"
    );
    expect(hash).to.equal(ethers.ZeroHash);
    expect(issuerAddress).to.equal(ethers.ZeroAddress);
    expect(status).to.equal(0); // None
    expect(await contract.checkCertificateStatus("CERT-UNKNOWN")).to.equal(0);
  });
});
