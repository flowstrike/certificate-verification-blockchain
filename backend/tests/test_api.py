"""Phase 2 API integration tests, updated for Phase 4 token auth.

Requires PostgreSQL. Run with DATABASE_URL pointing at a throwaway
test database, e.g.:
  DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/cert_verify_test
  pytest tests/test_api.py -v
Tables are created on import and cleared before each test; do NOT
point this at a database you care about.
"""

import hashlib
import os
from pathlib import Path

# Test uploads go to a separate folder, so tests never pollute backend/uploads/.
os.environ.setdefault("UPLOAD_DIR", str(Path(__file__).parent / "test_uploads"))

from fastapi.testclient import TestClient

from app.database import SessionLocal, init_db
from app.models import CertificateMetadata, Issuer, VerificationLog

init_db()

from app.main import app  # noqa: E402

client = TestClient(app)

ORIGINAL_PDF = b"%PDF-1.4 original certificate content"
MODIFIED_PDF = b"%PDF-1.4 original certificate contenT"  # one byte changed
ADMIN = {"email": "admin@demo.local", "password": "admin123"}
ISSUER_PASSWORD = "issuer123"


def _clear():
    db = SessionLocal()
    try:
        db.query(VerificationLog).delete()
        db.query(CertificateMetadata).delete()
        db.query(Issuer).delete()
        db.commit()
    finally:
        db.close()


def _admin_headers():
    r = client.post("/auth/login", json=ADMIN)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _create_issuer(wallet, password=ISSUER_PASSWORD, authorize=True):
    headers = _admin_headers()
    r = client.post(
        "/issuers",
        json={
            "college_name": "Test College",
            "wallet_address": wallet,
            "email": f"issuer-{wallet[-6:]}@test.local",
            "password": password,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    issuer_id = r.json()["id"]
    if authorize:
        r = client.patch(f"/issuers/{issuer_id}/authorize", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["authorization_status"] == "AUTHORIZED"
    r = client.post(
        "/auth/login",
        json={"email": f"issuer-{wallet[-6:]}@test.local", "password": password},
    )
    assert r.status_code == 200, r.text
    return issuer_id, {"Authorization": f"Bearer {r.json()['token']}"}


def _authorized_issuer():
    _clear()
    return _create_issuer("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")


def _upload(issuer_id, pdf_bytes, headers):
    return client.post(
        "/certificates",
        data={
            "student_name": "Test Student",
            "course": "BSc Computer Science",
            "college": "Test College",
            "issue_date": "2026-05-01",
            "issuer_id": str(issuer_id),
        },
        files={"file": ("certificate.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )


def test_upload_returns_id_and_correct_sha256():
    issuer_id, headers = _authorized_issuer()
    r = _upload(issuer_id, ORIGINAL_PDF, headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sha256_hash"] == hashlib.sha256(ORIGINAL_PDF).hexdigest()
    assert body["certificate_id"].startswith("CERT-")
    assert len(body["certificate_id"]) == 11  # CERT- + 6 chars
    # Phase 2: not on-chain yet, so it must NOT claim ACTIVE.
    assert body["blockchain_status"] == "NOT_REGISTERED_ONCHAIN"
    assert body["blockchain_tx_hash"] is None


def test_modified_file_gives_different_hash():
    issuer_id, headers = _authorized_issuer()
    r1 = _upload(issuer_id, ORIGINAL_PDF, headers)
    r2 = _upload(issuer_id, MODIFIED_PDF, headers)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["sha256_hash"] != r2.json()["sha256_hash"]
    assert r1.json()["certificate_id"] != r2.json()["certificate_id"]


def test_byte_identical_upload_gives_same_hash():
    issuer_id, headers = _authorized_issuer()
    r1 = _upload(issuer_id, ORIGINAL_PDF, headers)
    r2 = _upload(issuer_id, ORIGINAL_PDF, headers)
    assert r1.json()["sha256_hash"] == r2.json()["sha256_hash"]


def test_unauthorized_issuer_is_rejected():
    _clear()
    # Still PENDING, never authorized — but logged in, so the rejection
    # is the authorization check, not the login check.
    issuer_id, headers = _create_issuer(
        "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC", authorize=False
    )
    r = _upload(issuer_id, ORIGINAL_PDF, headers)
    assert r.status_code == 403
    assert "not authorized" in r.json()["detail"].lower()


def test_upload_without_login_is_rejected():
    issuer_id, _headers = _authorized_issuer()
    r = client.post(
        "/certificates",
        data={
            "student_name": "Test Student",
            "course": "BSc",
            "college": "Test College",
            "issue_date": "2026-05-01",
            "issuer_id": str(issuer_id),
        },
        files={"file": ("certificate.pdf", ORIGINAL_PDF, "application/pdf")},
    )
    assert r.status_code == 401


def test_create_issuer_requires_admin():
    _clear()
    r = client.post(
        "/issuers",
        json={"college_name": "Nope", "wallet_address": "0x0000000000000000000000000000000000000001"},
    )
    assert r.status_code == 401
    r = client.post("/auth/login", json={"email": "admin@demo.local", "password": "wrong"})
    assert r.status_code == 401


def test_non_pdf_is_rejected():
    issuer_id, headers = _authorized_issuer()
    r = client.post(
        "/certificates",
        data={
            "student_name": "Test Student",
            "course": "BSc",
            "college": "Test College",
            "issue_date": "2026-05-01",
            "issuer_id": str(issuer_id),
        },
        files={"file": ("certificate.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert r.status_code == 400


def test_lookup_and_download_round_trip():
    issuer_id, headers = _authorized_issuer()
    r = _upload(issuer_id, ORIGINAL_PDF, headers)
    cert_id = r.json()["certificate_id"]

    # Lookup and download are public (student / verifier access).
    r = client.get(f"/certificates/{cert_id}")
    assert r.status_code == 200
    assert r.json()["student_name"] == "Test Student"

    r = client.get(f"/certificates/{cert_id}/download")
    assert r.status_code == 200
    assert r.content == ORIGINAL_PDF

    r = client.get("/certificates/CERT-UNKNOWN")
    assert r.status_code == 404
