from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import auth, blockchain as blockchain_service
from .auth import get_admin_user, get_issuer_user
from .blockchain import BlockchainError, BlockchainNotConfigured
from .database import get_db, init_db
from .models import CertificateMetadata, Issuer, VerificationLog
from .schemas import (
    BlockchainConfirmIn,
    BlockchainRecordOut,
    CertificateOut,
    IssuerCreate,
    IssuerOut,
    LoginIn,
    LoginOut,
    VerificationLogOut,
    VerificationOut,
)
from .services import compute_sha256, generate_certificate_id, save_pdf, validate_pdf

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Blockchain-Based Academic Certificate Verification — Backend",
    description=(
        "Phase 2: FastAPI + PostgreSQL. Backend flow from the notes, "
        "Section 7, without blockchain wiring yet (Phase 3). "
        "A certificate registered here is NOT on-chain yet and must not "
        "be presented as ACTIVE until Phase 3."
    ),
    lifespan=lifespan,
)

# Phase 4: the React frontend runs on a different port (Vite, :5173),
# so the browser needs CORS. Local demo only: allow localhost origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


# ---------------------------------------------------------------- auth
@app.post("/auth/login", response_model=LoginOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """Login (Phase 4, confirmed Phase 0 decision 1).

    Admin: the single account from ADMIN_EMAIL / ADMIN_PASSWORD env
    (demo defaults in app/auth.py). Issuer: an Issuer row with a matching
    email and password hash. A PENDING issuer can log in but cannot
    register certificates until authorized (backend still returns 403
    on upload, and the frontend shows the pending state).
    """
    email = payload.email.strip().lower()
    if email == auth.ADMIN_EMAIL.lower() and payload.password == auth.ADMIN_PASSWORD:
        return LoginOut(token=auth.create_token("admin"), role="admin")
    issuer = db.query(Issuer).filter(Issuer.email == payload.email.strip()).first()
    if issuer and auth.verify_password(payload.password, issuer.password_hash):
        return LoginOut(
            token=auth.create_token("issuer", issuer.id),
            role="issuer",
            issuer_id=issuer.id,
            college_name=issuer.college_name,
            wallet_address=issuer.wallet_address,
            authorization_status=issuer.authorization_status,
        )
    raise HTTPException(status_code=401, detail="Invalid email or password")


@app.get("/auth/me")
def me(user: dict = Depends(auth.get_current_user)):
    return user


# ---------------------------------------------------------------- issuers
@app.post("/issuers", response_model=IssuerOut, status_code=201)
def create_issuer(
    payload: IssuerCreate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    """Create an issuer record. Starts as PENDING. Admin only (Phase 4)."""
    if not payload.college_name.strip() or not payload.wallet_address.strip():
        raise HTTPException(status_code=400, detail="College name and wallet address are required")
    issuer = Issuer(
        college_name=payload.college_name.strip(),
        wallet_address=payload.wallet_address.strip(),
        email=payload.email,
        password_hash=auth.hash_password(payload.password) if payload.password else None,
        authorization_status="PENDING",
    )
    db.add(issuer)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Issuer with this wallet address or email already exists")
    db.refresh(issuer)
    return issuer


@app.get("/issuers", response_model=list[IssuerOut])
def list_issuers(
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    return db.query(Issuer).order_by(Issuer.id).all()


@app.patch("/issuers/{issuer_id}/authorize", response_model=IssuerOut)
def authorize_issuer(
    issuer_id: int,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    """Admin authorizes an issuer in the database (notes, Section 4A).
    The contract-level authorization is separate (Phase 3: the wallet
    must also be authorized on-chain, via the Admin's authorize tx).
    """
    issuer = db.query(Issuer).filter(Issuer.id == issuer_id).first()
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found")
    issuer.authorization_status = "AUTHORIZED"
    db.commit()
    db.refresh(issuer)
    return issuer


# ------------------------------------------------------------ certificates
@app.post("/certificates", response_model=CertificateOut, status_code=201)
async def register_certificate(
    student_name: str = Form(...),
    course: str = Form(...),
    college: str = Form(...),
    issue_date: date = Form(...),
    issuer_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_issuer_user),
):
    """Backend registration flow (notes, Sections 7 and 15, minus the
    blockchain step, which is Phase 3):

    Validate request -> check issuer authorization -> generate
    Certificate ID -> calculate SHA-256 -> store metadata + PDF ->
    return result.

    Phase 4: the logged-in issuer can only register under their own
    issuer_id. A token for another issuer (or no token) is rejected.
    """
    if user["issuer_id"] != issuer_id:
        raise HTTPException(
            status_code=403, detail="Cannot register under another issuer"
        )
    # 1. Is the issuer authorized? (notes, Section 15: NO -> Reject)
    issuer = db.query(Issuer).filter(Issuer.id == issuer_id).first()
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found")
    if issuer.authorization_status != "AUTHORIZED":
        raise HTTPException(status_code=403, detail="Issuer not authorized")

    # 2. Validate the request fields.
    if not student_name.strip() or not course.strip() or not college.strip():
        raise HTTPException(
            status_code=400,
            detail="Student name, course, and college are required",
        )

    # 3. Read, validate, and hash the exact PDF bytes.
    data = await file.read()
    try:
        validate_pdf(file.filename or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    sha256_hash = compute_sha256(data)

    # 4. Generate a unique Certificate ID and store metadata + file.
    certificate_id = generate_certificate_id(db)
    saved_path = save_pdf(certificate_id, data)
    record = CertificateMetadata(
        certificate_id=certificate_id,
        student_name=student_name.strip(),
        course=course.strip(),
        college=college.strip(),
        certificate_file=str(saved_path),
        issue_date=issue_date,
        issuer_id=issuer.id,
        sha256_hash=sha256_hash,
        blockchain_tx_hash=None,
        # Phase 2: explicitly not on-chain yet. Phase 3 sets ACTIVE.
        blockchain_status="NOT_REGISTERED_ONCHAIN",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/certificates/{certificate_id}", response_model=CertificateOut)
def get_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """Record lookup by Certificate ID.

    IMPORTANT (notes, Section 18): finding a record here means
    "Record Found" only. It does NOT prove an uploaded file is valid.
    File verification (hash comparison) is Phase 5.
    """
    record = (
        db.query(CertificateMetadata)
        .filter(CertificateMetadata.certificate_id == certificate_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return record


@app.get("/issuers/{issuer_id}/certificates", response_model=list[CertificateOut])
def list_issuer_certificates(
    issuer_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(auth.get_current_user),
):
    # Admin may view any issuer's list; an issuer may view only their own.
    if user["role"] == "issuer" and user["issuer_id"] != issuer_id:
        raise HTTPException(status_code=403, detail="Cannot view another issuer's certificates")
    issuer = db.query(Issuer).filter(Issuer.id == issuer_id).first()
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found")
    return (
        db.query(CertificateMetadata)
        .filter(CertificateMetadata.issuer_id == issuer_id)
        .order_by(CertificateMetadata.id)
        .all()
    )


# ------------------------------------------------- blockchain (Phase 3)
@app.get("/blockchain/status")
def get_blockchain_status():
    """Is a contract configured and reachable? For Transaction Status (Phase 4)."""
    try:
        return blockchain_service.blockchain_status()
    except (BlockchainNotConfigured, BlockchainError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/certificates/{certificate_id}/blockchain", response_model=BlockchainRecordOut)
def get_blockchain_record(certificate_id: str):
    """Read the on-chain record for a certificate (no database claim)."""
    try:
        return blockchain_service.read_certificate(certificate_id)
    except BlockchainNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except BlockchainError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/issuers/{issuer_id}/blockchain-authorized")
def get_issuer_blockchain_authorization(issuer_id: int, db: Session = Depends(get_db)):
    issuer = db.query(Issuer).filter(Issuer.id == issuer_id).first()
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found")
    try:
        onchain = blockchain_service.is_issuer_authorized_onchain(issuer.wallet_address)
    except BlockchainNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except BlockchainError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {
        "issuer_id": issuer.id,
        "wallet_address": issuer.wallet_address,
        "authorized_in_database": issuer.authorization_status == "AUTHORIZED",
        "authorized_onchain": onchain,
    }


def _confirm_blockchain(
    db: Session,
    certificate_id: str,
    transaction_hash: str,
    expected_status: str,
    user: dict,
):
    """Shared confirm logic for registration (ACTIVE) and revocation (REVOKED).

    The backend trusts nothing the frontend claims: it checks the
    transaction receipt AND reads the contract record, and only updates
    the database when hash, issuer, and status all match. Otherwise the
    database status is left unchanged and the request fails.
    """
    record = (
        db.query(CertificateMetadata)
        .filter(CertificateMetadata.certificate_id == certificate_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if user["role"] == "issuer" and user["issuer_id"] != record.issuer_id:
        raise HTTPException(
            status_code=403, detail="Cannot confirm another issuer's certificate"
        )
    try:
        blockchain_service.check_transaction(transaction_hash)
        onchain = blockchain_service.read_certificate(certificate_id)
    except BlockchainNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except BlockchainError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if onchain["hash"].lower() != ("0x" + record.sha256_hash).lower():
        raise HTTPException(
            status_code=409,
            detail="On-chain hash does not match the stored certificate hash",
        )
    if onchain["issuer"].lower() != record.issuer.wallet_address.lower():
        raise HTTPException(
            status_code=409,
            detail="On-chain issuer does not match the certificate issuer",
        )
    if onchain["status"] != expected_status:
        raise HTTPException(
            status_code=409,
            detail=(
                f"On-chain status is {onchain['status']}, "
                f"expected {expected_status}"
            ),
        )
    record.blockchain_tx_hash = transaction_hash
    record.blockchain_status = expected_status
    db.commit()
    db.refresh(record)
    return record


@app.post("/certificates/{certificate_id}/confirm-blockchain", response_model=CertificateOut)
def confirm_blockchain(
    certificate_id: str,
    payload: BlockchainConfirmIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_issuer_user),
):
    """After React + ethers.js sends the register transaction (Phase 4),
    the frontend calls this with the transaction hash. The backend
    verifies on-chain and only then marks the certificate ACTIVE.
    """
    return _confirm_blockchain(db, certificate_id, payload.transaction_hash, "ACTIVE", user)


@app.post("/certificates/{certificate_id}/confirm-revocation", response_model=CertificateOut)
def confirm_revocation(
    certificate_id: str,
    payload: BlockchainConfirmIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_issuer_user),
):
    """After React + ethers.js sends the revoke transaction (Phase 4),
    the frontend calls this with the transaction hash. The backend
    verifies on-chain and only then marks the certificate REVOKED.
    """
    return _confirm_blockchain(db, certificate_id, payload.transaction_hash, "REVOKED", user)


@app.get("/verification-logs", response_model=list[VerificationLogOut])
def list_verification_logs(
    certificate_id: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(auth.get_current_user),
):
    """Verification History (notes, Sections 6 and 8).

    Phase 4: the page exists and lists whatever is logged. Rows are
    written by the verification endpoint in Phase 5, so this list is
    empty until then — that is expected, not an error.
    """
    query = db.query(VerificationLog).order_by(VerificationLog.id.desc())
    if certificate_id:
        query = query.filter(VerificationLog.certificate_id == certificate_id)
    return query.limit(200).all()


# ------------------------------------------------ verification (Phase 5)
@app.post("/verify", response_model=VerificationOut)
async def verify_certificate(
    file: UploadFile = File(...),
    certificate_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """File verification, notes Section 16, in exactly this order:

    Upload PDF -> SHA-256 -> Get Blockchain Record -> Record Exists?
    (NO -> NOT FOUND) -> Revoked? (YES -> REVOKED) -> Compare Hash
    (YES -> VALID, NO -> MODIFIED).

    Every result is written to VerificationLog (notes, Section 8).

    IMPORTANT — why MODIFIED needs a Certificate ID (Phase 5 finding,
    not a rule from the notes): a SHA-256 hash is one-way. A modified
    file has a brand-new hash, and no hash-to-original lookup can tell
    which original it was changed from. So:
    - With a Certificate ID, the system knows which on-chain record to
      compare the uploaded hash against, and a mismatch is MODIFIED.
    - Without an ID, the system first finds a record by the uploaded
      hash in PostgreSQL. If the hash matches a record, that record's
      ID is used for the on-chain check. If no record matches the hash,
      no record can be identified, so the result is NOT FOUND — not a
      guessed MODIFIED.
    The contract is keyed by Certificate ID, not by hash (notes,
    Section 9), so a hash-only lookup without a database match cannot
    reach the blockchain at all. The frontend explains this and asks
    for the ID when a verifier suspects modification.

    The blockchain record is the source of truth for the result, not
    the database: a database record whose on-chain record is missing
    verifies as NOT FOUND, and a revoked on-chain record verifies as
    REVOKED even when the uploaded file is byte-identical.
    """
    data = await file.read()
    try:
        validate_pdf(file.filename or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    uploaded_hash = compute_sha256(data)

    supplied_id = certificate_id.strip() if certificate_id else None
    db_record = None
    resolved_id = None
    if supplied_id:
        resolved_id = supplied_id
        db_record = (
            db.query(CertificateMetadata)
            .filter(CertificateMetadata.certificate_id == supplied_id)
            .first()
        )
    else:
        db_record = (
            db.query(CertificateMetadata)
            .filter(CertificateMetadata.sha256_hash == uploaded_hash)
            .first()
        )
        if db_record:
            resolved_id = db_record.certificate_id

    def _log_and_return(result: str, onchain: dict | None):
        log_id = resolved_id if resolved_id else "UNKNOWN"
        db.add(
            VerificationLog(
                certificate_id=log_id, verification_result=result
            )
        )
        db.commit()
        return VerificationOut(
            certificate_id=resolved_id,
            verification_result=result,
            uploaded_sha256_hash=uploaded_hash,
            stored_sha256_hash=(
                onchain["hash"] if onchain and onchain["exists"] else None
            ),
            onchain_status=onchain["status"] if onchain else None,
            issuer_address=(
                onchain["issuer"] if onchain and onchain["exists"] else None
            ),
            student_name=db_record.student_name if db_record else None,
            course=db_record.course if db_record else None,
            college=db_record.college if db_record else None,
        )

    if resolved_id is None:
        # No ID supplied and no database record matches the uploaded hash.
        return _log_and_return("NOT_FOUND", None)

    try:
        onchain = blockchain_service.read_certificate(resolved_id)
    except BlockchainNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except BlockchainError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if not onchain["exists"] or onchain["status"] == "NOT_FOUND":
        return _log_and_return("NOT_FOUND", onchain)
    if onchain["status"] == "REVOKED":
        return _log_and_return("REVOKED", onchain)
    if onchain["status"] == "ACTIVE":
        if uploaded_hash.lower() == onchain["hash"].lower().removeprefix("0x"):
            return _log_and_return("VALID", onchain)
        return _log_and_return("MODIFIED", onchain)
    return _log_and_return("NOT_FOUND", onchain)


@app.get("/certificates/{certificate_id}/download")
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """Student download (notes, Section 4C; frontend in Phase 4)."""
    record = (
        db.query(CertificateMetadata)
        .filter(CertificateMetadata.certificate_id == certificate_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return FileResponse(
        record.certificate_file,
        media_type="application/pdf",
        filename=f"{certificate_id}.pdf",
    )
