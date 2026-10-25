from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class IssuerCreate(BaseModel):
    college_name: str
    wallet_address: str
    email: str | None = None
    password: str | None = None


class IssuerOut(BaseModel):
    id: int
    college_name: str
    wallet_address: str
    authorization_status: str
    email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    token: str
    role: str
    issuer_id: int | None = None
    college_name: str | None = None
    wallet_address: str | None = None
    authorization_status: str | None = None


class VerificationOut(BaseModel):
    certificate_id: str | None = None
    verification_result: str
    uploaded_sha256_hash: str
    stored_sha256_hash: str | None = None
    onchain_status: str | None = None
    issuer_address: str | None = None
    student_name: str | None = None
    course: str | None = None
    college: str | None = None


class VerificationLogOut(BaseModel):
    id: int
    certificate_id: str
    verification_date: datetime
    verification_result: str

    model_config = ConfigDict(from_attributes=True)


class CertificateOut(BaseModel):
    certificate_id: str
    student_name: str
    course: str
    college: str
    certificate_file: str
    issue_date: date
    issuer_id: int
    sha256_hash: str
    blockchain_tx_hash: str | None = None
    # Phase 2: null / NOT_REGISTERED_ONCHAIN until Phase 3 registers it
    # on-chain and sets this to ACTIVE. Never claim ACTIVE before then.
    blockchain_status: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlockchainConfirmIn(BaseModel):
    transaction_hash: str


class BlockchainRecordOut(BaseModel):
    certificate_id: str
    hash: str
    issuer: str
    status: str
    exists: bool


class CertificateRegisteredOut(CertificateOut):
    """Same as CertificateOut; kept separate so Phase 3 can add the
    transaction hash to the registration response without changing
    the lookup response shape."""

    pass
