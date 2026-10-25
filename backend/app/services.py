import hashlib
import secrets
import string
from pathlib import Path

from sqlalchemy.orm import Session

from .config import MAX_PDF_SIZE_BYTES, UPLOAD_DIR
from .models import CertificateMetadata

_ALPHABET = string.ascii_uppercase + string.digits


def compute_sha256(data: bytes) -> str:
    """SHA-256 fingerprint of the exact file bytes (notes, Section 10)."""
    return hashlib.sha256(data).hexdigest()


def generate_certificate_id(db: Session) -> str:
    """Certificate ID, confirmed Phase 0 decision 3.

    Format CERT- + 6 uppercase letters/digits, following the notes'
    example CERT-X7K29A. The notes give no generation rule, so uniqueness
    is checked against the database here.
    """
    for _ in range(100):
        candidate = "CERT-" + "".join(secrets.choice(_ALPHABET) for _ in range(6))
        exists = (
            db.query(CertificateMetadata)
            .filter(CertificateMetadata.certificate_id == candidate)
            .first()
        )
        if not exists:
            return candidate
    raise RuntimeError("Could not generate a unique Certificate ID")


def validate_pdf(filename: str, data: bytes) -> None:
    """Validate an uploaded certificate file. Raises ValueError on failure.

    Checks: .pdf extension, PDF magic bytes (%PDF), and the size safeguard
    from config.py. The notes specify PDF as the certificate format; the
    magic-byte check is the implementation of that rule.
    """
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Certificate file must be a PDF")
    if len(data) > MAX_PDF_SIZE_BYTES:
        raise ValueError("Certificate file is too large (max 10 MB)")
    if not data.startswith(b"%PDF"):
        raise ValueError("Uploaded file is not a valid PDF")


def save_pdf(certificate_id: str, data: bytes) -> Path:
    """Store the PDF on disk (confirmed Phase 0 decision 4).

    Returns the path stored in CertificateMetadata.certificate_file.
    Never stored on the blockchain (notes, Section 8).
    """
    path = UPLOAD_DIR / f"{certificate_id}.pdf"
    path.write_bytes(data)
    return path
