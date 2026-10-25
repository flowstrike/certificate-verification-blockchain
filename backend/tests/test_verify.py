"""Phase 5 /verify tests, with the blockchain service mocked.

The live-chain proof is tests/phase5_live_check.py. Here, mocking
read_certificate lets each Section 16 outcome be tested in isolation.
"""

import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("UPLOAD_DIR", str(Path(__file__).parent / "test_uploads"))
os.environ.setdefault("CONTRACT_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import CertificateMetadata, Issuer, VerificationLog  # noqa: E402

init_db()

from app.main import app  # noqa: E402

client = TestClient(app)

ORIGINAL = b"%PDF-1.4 phase5 original certificate"
MODIFIED = b"%PDF-1.4 phase5 original certificatE"  # one byte changed
ISSUER_WALLET = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"


def _clear():
    db = SessionLocal()
    try:
        db.query(VerificationLog).delete()
        db.query(CertificateMetadata).delete()
        db.query(Issuer).delete()
        db.commit()
    finally:
        db.close()


def _setup_cert():
    _clear()
    r = client.post("/auth/login", json={"email": "admin@demo.local", "password": "admin123"})
    admin_headers = {"Authorization": f"Bearer {r.json()['token']}"}
    r = client.post(
        "/issuers",
        json={
            "college_name": "Test College",
            "wallet_address": ISSUER_WALLET,
            "email": "issuer-verify@test.local",
            "password": "issuer123",
        },
        headers=admin_headers,
    )
    issuer_id = r.json()["id"]
    client.patch(f"/issuers/{issuer_id}/authorize", headers=admin_headers)
    r = client.post(
        "/auth/login",
        json={"email": "issuer-verify@test.local", "password": "issuer123"},
    )
    headers = {"Authorization": f"Bearer {r.json()['token']}"}
    r = client.post(
        "/certificates",
        data={
            "student_name": "Test Student",
            "course": "BSc",
            "college": "Test College",
            "issue_date": "2026-05-01",
            "issuer_id": str(issuer_id),
        },
        files={"file": ("certificate.pdf", ORIGINAL, "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json(), headers


def _onchain(cert, status):
    return {
        "certificate_id": cert["certificate_id"],
        "hash": "0x" + cert["sha256_hash"],
        "issuer": ISSUER_WALLET,
        "status": status,
        "exists": status != "NOT_FOUND",
    }


def _verify(pdf_bytes, cert_id=None):
    data = {}
    if cert_id:
        data["certificate_id"] = cert_id
    return client.post(
        "/verify",
        data=data,
        files={"file": ("certificate.pdf", pdf_bytes, "application/pdf")},
    )


def _logs(headers):
    r = client.get("/verification-logs", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_verify_original_no_id_is_valid_and_logged():
    cert, headers = _setup_cert()
    with patch("app.main.blockchain_service.read_certificate",
               return_value=_onchain(cert, "ACTIVE")):
        r = _verify(ORIGINAL)
    assert r.status_code == 200, r.text
    assert r.json()["verification_result"] == "VALID"
    assert r.json()["certificate_id"] == cert["certificate_id"]
    logs = _logs(headers)
    assert len(logs) == 1
    assert logs[0]["verification_result"] == "VALID"
    assert logs[0]["certificate_id"] == cert["certificate_id"]


def test_verify_modified_with_id_is_modified():
    cert, headers = _setup_cert()
    with patch("app.main.blockchain_service.read_certificate",
               return_value=_onchain(cert, "ACTIVE")):
        r = _verify(MODIFIED, cert_id=cert["certificate_id"])
    assert r.json()["verification_result"] == "MODIFIED"


def test_verify_modified_without_id_is_not_found_not_guessed_modified():
    cert, headers = _setup_cert()
    # No mock needed: hash lookup fails, so no on-chain call is made.
    r = _verify(MODIFIED)
    assert r.json()["verification_result"] == "NOT_FOUND"
    assert r.json()["certificate_id"] is None


def test_verify_revoked_original_is_revoked_not_valid():
    cert, headers = _setup_cert()
    with patch("app.main.blockchain_service.read_certificate",
               return_value=_onchain(cert, "REVOKED")):
        r = _verify(ORIGINAL, cert_id=cert["certificate_id"])
    assert r.json()["verification_result"] == "REVOKED"


def test_verify_unknown_id_is_not_found_and_logged():
    cert, headers = _setup_cert()
    with patch("app.main.blockchain_service.read_certificate",
               return_value=_onchain({**cert, "certificate_id": "CERT-UNKNOWN"}, "NOT_FOUND")):
        r = _verify(ORIGINAL, cert_id="CERT-UNKNOWN")
    assert r.json()["verification_result"] == "NOT_FOUND"
    logs = _logs(headers)
    assert logs[-1]["certificate_id"] == "CERT-UNKNOWN"
    assert logs[-1]["verification_result"] == "NOT_FOUND"


def test_verify_non_pdf_is_rejected():
    cert, headers = _setup_cert()
    r = client.post(
        "/verify",
        files={"file": ("certificate.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400


def test_id_lookup_is_not_a_verification_result():
    cert, headers = _setup_cert()
    r = client.get(f"/certificates/{cert['certificate_id']}")
    assert r.status_code == 200
    # Lookup returns metadata, never a verification_result field.
    assert "verification_result" not in r.json()
    # And lookup alone writes no verification log.
    assert _logs(headers) == []
