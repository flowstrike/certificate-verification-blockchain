// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @title CertificateVerification
/// @notice Phase 1 of the Blockchain-Based Academic Certificate Verification System.
/// @dev Implements exactly the five operations from the project notes, Section 11:
///      Authorize Issuer, Register Certificate, Get Certificate Record,
///      Revoke Certificate, Check Certificate Status.
///      On-chain data is ONLY (notes, Section 9):
///      Certificate ID + SHA-256 Hash + Issuer Address + Certificate Status.
///      Personal information and the full certificate PDF are NEVER stored here
///      (notes, Section 8). The hash is stored as an opaque bytes32: in the real
///      system the backend (Phase 2) computes the SHA-256 of the exact PDF bytes
///      and passes those 32 bytes here. This contract does not hash anything
///      itself, so it never sees the PDF.
///      Revocation changes status ACTIVE -> REVOKED and never deletes the record
///      (notes, Section 17).
///      Authorization rule (notes, Sections 11 and 17): only an authorized
///      issuer may register or revoke. The notes do NOT state an additional
///      "original issuer only" restriction for revocation, so none is added here.
contract CertificateVerification {
    address public admin;

    mapping(address => bool) public authorizedIssuers;

    /// @dev None = no record (maps to NOT FOUND in the verification flow).
    ///      Active / Revoked map to the notes' ACTIVE / REVOKED statuses.
    enum Status {
        None,
        Active,
        Revoked
    }

    struct Certificate {
        bytes32 certHash;
        address issuer;
        Status status;
    }

    mapping(string => Certificate) private certificates;

    event IssuerAuthorized(address indexed issuer, address indexed admin);
    event CertificateRegistered(
        string indexed certId,
        bytes32 certHash,
        address indexed issuer
    );
    event CertificateRevoked(string indexed certId, address indexed issuer);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }

    modifier onlyAuthorizedIssuer() {
        require(authorizedIssuers[msg.sender], "Only authorized issuer");
        _;
    }

    /// @dev The deployer is the admin. In the demo (confirmed Phase 0
    ///      decision 9) this is Hardhat account 0.
    constructor() {
        admin = msg.sender;
    }

    /// @notice Authorize Issuer (notes, Section 11). Admin only.
    function authorizeIssuer(address issuer) external onlyAdmin {
        require(issuer != address(0), "Invalid issuer address");
        authorizedIssuers[issuer] = true;
        emit IssuerAuthorized(issuer, msg.sender);
    }

    /// @notice Register Certificate (notes, Section 11).
    /// @dev Authorized issuers only. A Certificate ID can be registered once.
    function registerCertificate(
        string calldata certId,
        bytes32 certHash
    ) external onlyAuthorizedIssuer {
        require(bytes(certId).length > 0, "Empty certificate ID");
        require(certHash != bytes32(0), "Empty certificate hash");
        require(
            certificates[certId].status == Status.None,
            "Certificate already exists"
        );
        certificates[certId] = Certificate({
            certHash: certHash,
            issuer: msg.sender,
            status: Status.Active
        });
        emit CertificateRegistered(certId, certHash, msg.sender);
    }

    /// @notice Get Certificate Record (notes, Section 11).
    /// @return certHash SHA-256 hash stored for this ID (0 if no record).
    /// @return issuer Address that registered it (0 address if no record).
    /// @return status None / Active / Revoked.
    function getCertificateRecord(
        string calldata certId
    )
        external
        view
        returns (bytes32 certHash, address issuer, Status status)
    {
        Certificate storage cert = certificates[certId];
        return (cert.certHash, cert.issuer, cert.status);
    }

    /// @notice Check Certificate Status (notes, Section 11).
    /// @return Status None (not found), Active, or Revoked.
    function checkCertificateStatus(
        string calldata certId
    ) external view returns (Status) {
        return certificates[certId].status;
    }

    /// @notice Revoke Certificate (notes, Section 11 and 17).
    /// @dev Authorized issuers only. Status changes Active -> Revoked;
    ///      the record, its hash, and its issuer remain readable afterwards.
    function revokeCertificate(string calldata certId) external onlyAuthorizedIssuer {
        Certificate storage cert = certificates[certId];
        require(cert.status == Status.Active, "Certificate not active");
        cert.status = Status.Revoked;
        emit CertificateRevoked(certId, msg.sender);
    }
}
