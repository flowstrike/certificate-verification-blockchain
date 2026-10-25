"""Phase 3 confirm-endpoint tests with the blockchain service mocked.

These tests prove the endpoint logic (only mark ACTIVE/REVOKED when the
on-chain record matches) without needing a live chain. The live chain
proof is tests/phase3_live_check.py, which runs Hardhat + backend for real.
"""

import os
from pathlib import Path

os.environ.setdefault("UPLOAD_DIR", str(Path(__file__).parent / "test_uploads"))
# A dummy address is enough: the service is mocked, so no RPC call happens.
os.environ.setdefault("CONTRACT_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")

from unittest.mock import patch  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import CertificateMetadata, Issuer, VerificationLog  # noqa: E402

init_db()

from app.main import app  # noqa: E402

client = TestClient(app)

PDF = b"%PDF-1.4 phase3 test certificate"
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
    assert r.status_code == 200, r.text
    admin_headers = {"Authorization": f"Bearer {r.json()['token']}"}
    r = client.post(
        "/issuers",
        json={
            "college_name": "Test College",
            "wallet_address": ISSUER_WALLET,
            "email": "issuer-confirm@test.local",
            "password": "issuer123",
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    issuer_id = r.json()["id"]
    r = client.patch(f"/issuers/{issuer_id}/authorize", headers=admin_headers)
    assert r.status_code == 200, r.text
    r = client.post(
        "/auth/login",
        json={"email": "issuer-confirm@test.local", "password": "issuer123"},
    )
    assert r.status_code == 200, r.text
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
        files={"file": ("certificate.pdf", PDF, "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json(), headers


def test_confirm_marks_active_when_onchain_matches():
    cert, headers = _setup_cert()
    onchain = {
        "certificate_id": cert["certificate_id"],
        "hash": "0x" + cert["sha256_hash"],
        "issuer": ISSUER_WALLET,
        "status": "ACTIVE",
        "exists": True,
    }
    with patch("app.main.blockchain_service.check_transaction", return_value={"status": "mined"}), patch(
        "app.main.blockchain_service.read_certificate", return_value=onchain
    ):
        r = client.post(
            f"/certificates/{cert['certificate_id']}/confirm-blockchain",
            json={"transaction_hash": "0x" + "ab" * 32},
            headers=headers,
        )
    assert r.status_code == 200, r.text
    assert r.json()["blockchain_status"] == "ACTIVE"
    assert r.json()["blockchain_tx_hash"] == "0x" + "ab" * 32


def test_confirm_rejects_mismatched_hash_and_leaves_status_unchanged():
    cert, headers = _setup_cert()
    onchain = {
        "certificate_id": cert["certificate_id"],
        "hash": "0x" + "00" * 32,  # different hash
        "issuer": ISSUER_WALLET,
        "status": "ACTIVE",
        "exists": True,
    }
    with patch("app.main.blockchain_service.check_transaction", return_value={"status": "mined"}), patch(
        "app.main.blockchain_service.read_certificate", return_value=onchain
    ):
        r = client.post(
            f"/certificates/{cert['certificate_id']}/confirm-blockchain",
            json={"transaction_hash": "0x" + "ab" * 32},
            headers=headers,
        )
    assert r.status_code == 409
    r = client.get(f"/certificates/{cert['certificate_id']}")
    assert r.json()["blockchain_status"] == "NOT_REGISTERED_ONCHAIN"


def test_confirm_rejects_wrong_onchain_status():
    cert, headers = _setup_cert()
    onchain = {
        "certificate_id": cert["certificate_id"],
        "hash": "0x" + cert["sha256_hash"],
        "issuer": ISSUER_WALLET,
        "status": "NOT_FOUND",  # nothing registered yet
        "exists": False,
    }
    with patch("app.main.blockchain_service.check_transaction", return_value={"status": "mined"}), patch(
        "app.main.blockchain_service.read_certificate", return_value=onchain
    ):
        r = client.post(
            f"/certificates/{cert['certificate_id']}/confirm-blockchain",
            json={"transaction_hash": "0x" + "ab" * 32},
            headers=headers,
        )
    assert r.status_code == 409


def test_confirm_revocation_marks_revoked_when_onchain_revoked():
    cert, headers = _setup_cert()
    active = {
        "certificate_id": cert["certificate_id"],
        "hash": "0x" + cert["sha256_hash"],
        "issuer": ISSUER_WALLET,
        "status": "ACTIVE",
        "exists": True,
    }
    revoked = {**active, "status": "REVOKED"}
    with patch("app.main.blockchain_service.check_transaction", return_value={"status": "mined"}), patch(
        "app.main.blockchain_service.read_certificate", return_value=active
    ):
        r = client.post(
            f"/certificates/{cert['certificate_id']}/confirm-blockchain",
            json={"transaction_hash": "0x" + "ab" * 32},
            headers=headers,
        )
    assert r.json()["blockchain_status"] == "ACTIVE"
    with patch("app.main.blockchain_service.check_transaction", return_value={"status": "mined"}), patch(
        "app.main.blockchain_service.read_certificate", return_value=revoked
    ):
        r = client.post(
            f"/certificates/{cert['certificate_id']}/confirm-revocation",
            json={"transaction_hash": "0x" + "cd" * 32},
            headers=headers,
        )
    assert r.status_code == 200, r.text
    assert r.json()["blockchain_status"] == "REVOKED"
