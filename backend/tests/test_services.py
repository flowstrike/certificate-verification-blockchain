"""Unit tests that need no database: hashing, ID format, PDF validation."""

import hashlib
import re

import pytest

from app.services import compute_sha256, validate_pdf


def test_sha256_matches_hashlib():
    data = b"%PDF-1.4 sample certificate"
    assert compute_sha256(data) == hashlib.sha256(data).hexdigest()
    assert len(compute_sha256(data)) == 64  # 256 bits, hex-encoded


def test_sha256_changes_when_one_byte_changes():
    original = b"%PDF-1.4 original"
    modified = b"%PDF-1.4 originaL"  # one byte changed
    assert compute_sha256(original) != compute_sha256(modified)


def test_pdf_validation_accepts_real_pdf_bytes():
    validate_pdf("cert.pdf", b"%PDF-1.4 hello")


def test_pdf_validation_rejects_non_pdf():
    with pytest.raises(ValueError):
        validate_pdf("cert.txt", b"hello")
    with pytest.raises(ValueError):
        validate_pdf("cert.pdf", b"not a pdf at all")


def test_certificate_id_format_regex():
    # Format only (generation itself needs a database, tested in test_api.py).
    assert re.fullmatch(r"CERT-[A-Z0-9]{6}", "CERT-X7K29A")
