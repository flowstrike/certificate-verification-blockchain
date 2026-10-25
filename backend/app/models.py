from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Issuer(Base):
    """Issuer record — notes, Section 8.

    Notes fields: Issuer ID, College Name, Wallet Address, Authorization Status.
    Extra columns (email, password_hash, created_at) are Phase 0 / Phase 4
    implementation extensions: the confirmed Phase 0 decision is email +
    password login for Admin/Issuer, and login is built in Phase 4. Phase 2
    does not use password_hash yet.
    Authorization Status values used here: PENDING, AUTHORIZED.
    The notes do not name the values; these are the implementation choice.
    """

    __tablename__ = "issuers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    college_name: Mapped[str] = mapped_column(String, nullable=False)
    wallet_address: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    authorization_status: Mapped[str] = mapped_column(
        String, nullable=False, default="PENDING"
    )
    email: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    certificates: Mapped[list["CertificateMetadata"]] = relationship(
        "CertificateMetadata", back_populates="issuer"
    )


class CertificateMetadata(Base):
    """Certificate metadata — notes, Section 8.

    Notes fields: Certificate ID, Student Name, Course, Certificate File,
    Issue Date.
    Extra columns are needed for the confirmed decisions and for Phase 3:
    issuer_id (which issuer registered it, so authorization and issuer
    lists work), sha256_hash (the backend computes it in Phase 2 and sends
    it to the contract in Phase 3), blockchain_tx_hash and
    blockchain_status (filled in Phase 3; null in Phase 2, meaning the
    certificate has NOT been registered on-chain yet and must not be
    presented as ACTIVE).
    """

    __tablename__ = "certificate_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    certificate_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    student_name: Mapped[str] = mapped_column(String, nullable=False)
    course: Mapped[str] = mapped_column(String, nullable=False)
    college: Mapped[str] = mapped_column(String, nullable=False)
    certificate_file: Mapped[str] = mapped_column(String, nullable=False)
    issue_date = mapped_column(Date, nullable=False)
    issuer_id: Mapped[int] = mapped_column(Integer, ForeignKey("issuers.id"), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String, nullable=False)
    blockchain_tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    blockchain_status: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    issuer: Mapped[Issuer] = relationship("Issuer", back_populates="certificates")


class VerificationLog(Base):
    """Verification history — notes, Section 8.

    Notes fields: Verification ID, Certificate ID, Verification Date,
    Verification Result.
    certificate_id is intentionally NOT a foreign key: a verification
    attempt for an unknown ID (NOT FOUND, notes Section 16) must still be
    loggable. Rows are written by the verification endpoint in Phase 5;
    Phase 2 only creates the table.
    """

    __tablename__ = "verification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    certificate_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    verification_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    verification_result: Mapped[str] = mapped_column(String, nullable=False)
