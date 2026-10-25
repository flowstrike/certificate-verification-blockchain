"""Phase 6 acceptance demonstration (notes, Section 19).

Creates 10 synthetic/sample certificates and demonstrates, in order:
  1. Register 10 certificates.
  2. Upload an original certificate -> VALID.
  3. Modify one byte/file content and upload it -> MODIFIED.
  4. Revoke one certificate -> REVOKED.
  5. Search an unknown Certificate ID -> NOT FOUND.
  6. Try to issue a certificate using an unauthorized account -> REJECTED.
  7. Test smart-contract permissions automatically.

All certificates are SYNTHETIC samples, clearly labelled as such inside
each PDF. They are not real credentials and no real student data is used.

How MODIFIED is demonstrated (Phase 5 finding): a modified file's new
SHA-256 cannot identify its original, so case 3 supplies the Certificate
ID of the original, exactly as the Verify page explains. The modified
file itself is a genuine one-byte change: the first letter of the
student's name in the PDF is replaced (same length, so the PDF stays
valid and viewable), and the script asserts exactly one byte differs.

Prerequisites: PostgreSQL running, backend + blockchain dependencies
installed, reportlab installed in the backend venv.
  cd backend && .venv/bin/pip install reportlab
  su postgres -c "createdb certificate_demo"   (once)

Run from the repo root (or anywhere; paths are absolute from this file):
  backend/.venv/bin/python demo/run_demo.py
  backend/.venv/bin/python demo/run_demo.py --keep-servers

--keep-servers leaves the Hardhat node (port 8545) and backend
(port 8001) running afterwards, so you can then open the frontend
(see demo/README.md) and show the same 10 certificates there. By
default both servers are stopped at the end of the run.

Output: demo/DEMO_RESULT.md (this run's actual IDs, hashes, and
transaction hashes — they differ on every run because Certificate IDs
are generated randomly) plus a PASS/FAIL summary on stdout. The script
exits non-zero if any case fails.
"""

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
BLOCKCHAIN = ROOT / "blockchain"
DEMO_DIR = ROOT / "demo"
CERTS_DIR = DEMO_DIR / "certificates"
ISSUER_WALLET = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # Hardhat account 1
PENDING_WALLET = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"  # Hardhat account 2
TEST_DB = "postgresql+psycopg2://postgres:postgres@localhost:5432/certificate_demo"
API = "http://127.0.0.1:8001"

STUDENTS = [
    ("Aarav Sharma", "BSc Computer Science", "2026-04-15"),
    ("Priya Patel", "BCom", "2026-04-16"),
    ("Rohan Verma", "BSc Mathematics", "2026-04-17"),
    ("Sneha Kulkarni", "BA English", "2026-04-18"),
    ("Arjun Mehta", "BTech Information Technology", "2026-04-20"),
    ("Kavya Nair", "BSc Physics", "2026-04-21"),
    ("Vikram Singh", "BBA", "2026-04-22"),
    ("Ananya Iyer", "BSc Chemistry", "2026-04-23"),
    ("Aditya Joshi", "BCom Accounting", "2026-04-24"),
    ("Meera Desai", "BA Economics", "2026-04-25"),
]

processes = []
cases = []


def log(msg):
    print(f"[demo] {msg}", flush=True)


def record(name, expected, actual, passed, detail=""):
    cases.append(
        {"name": name, "expected": expected, "actual": actual,
         "passed": passed, "detail": detail}
    )
    log(f"{'PASS' if passed else 'FAIL'}: {name} — expected {expected}, got {actual} {detail}")


def start(cmd, cwd, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,
    )
    processes.append(proc)
    return proc


def stop_all():
    for proc in processes:
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
    processes.clear()


def wait_for(url, timeout=30, name="service"):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"{name} did not become ready at {url}")


def wait_for_rpc(timeout=30):
    deadline = time.time() + timeout
    payload = json.dumps(
        {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}
    ).encode()
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8545", data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    raise RuntimeError("Hardhat node did not become ready")


def http(method, url, data=None, files=None, headers=None):
    if files is None:
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
    else:
        boundary = uuid.uuid4().hex
        parts = []
        for key, value in (data or {}).items():
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; "
                f'name="{key}"\r\n\r\n{value}\r\n'.encode()
            )
        for key, (filename, content, mime) in files.items():
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; '
                f'name="{key}"; filename="{filename}"\r\n'
                f"Content-Type: {mime}\r\n\r\n".encode()
                + content
                + b"\r\n"
            )
        parts.append(f"--{boundary}--\r\n".encode())
        hdrs = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        hdrs.update(headers or {})
        req = urllib.request.Request(url, data=b"".join(parts), method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read() or b"{}"
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, {"raw": raw.decode(errors="replace")}
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            return exc.code, json.loads(body or b"{}")
        except json.JSONDecodeError:
            return exc.code, {"raw": body.decode(errors="replace")}


def run_hardhat_script(env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    result = subprocess.run(
        ["npx", "hardhat", "run", "scripts/submit_tx.js", "--network", "localhost"],
        cwd=BLOCKCHAIN, env=env, capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"submit_tx.js failed:\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout.strip().splitlines()[-1])


def make_pdfs():
    """Generate 10 synthetic PDFs, uncompressed so a one-byte edit is clean."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError(
            "reportlab is required for the demo. Run: "
            "cd backend && .venv/bin/pip install reportlab"
        ) from exc
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (name, course, issue_date) in enumerate(STUDENTS, start=1):
        path = CERTS_DIR / f"cert-{i:02d}.pdf"
        c = canvas.Canvas(str(path), pagesize=A4, pageCompression=0)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(297, 750, "CERTIFICATE")
        c.setFont("Helvetica", 12)
        c.drawString(72, 700, "This is a synthetic sample certificate for demo purposes only.")
        c.drawString(72, 660, f"Student: {name}")
        c.drawString(72, 630, f"Course: {course}")
        c.drawString(72, 600, "College: Demo College")
        c.drawString(72, 570, f"Issue Date: {issue_date}")
        c.drawString(72, 530, "This certificate is not a real credential.")
        c.showPage()
        c.save()
        assert path.read_bytes().startswith(b"%PDF"), f"{path} is not a PDF"
        assert name.encode() in path.read_bytes(), f"{path} does not contain the student name"
        paths.append(path)
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-servers", action="store_true",
                        help="Leave Hardhat node + backend running afterwards for a frontend demo")
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc).isoformat()
    contract = ""
    registered = []  # list of dicts: student, course, cert_id, hash, tx_hash, status
    try:
        # Clear the demo database.
        log("Clearing demo database tables")
        subprocess.run(
            [sys.executable, "-c",
             "from app.database import SessionLocal, Base, engine; "
             "from app.models import CertificateMetadata, Issuer, VerificationLog; "
             "Base.metadata.create_all(bind=engine); "
             "db = SessionLocal(); "
             "db.query(VerificationLog).delete(); "
             "db.query(CertificateMetadata).delete(); "
             "db.query(Issuer).delete(); db.commit()"],
            cwd=BACKEND, check=True,
            env={**os.environ, "DATABASE_URL": TEST_DB},
        )

        # Hardhat node + deploy.
        log("Starting Hardhat node")
        start(["npx", "hardhat", "node"], cwd=BLOCKCHAIN)
        wait_for_rpc()
        result = subprocess.run(
            ["npx", "hardhat", "run", "scripts/deploy.js", "--network", "localhost"],
            cwd=BLOCKCHAIN, capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"deploy failed:\n{result.stdout}\n{result.stderr}")
        contract = re.search(r"deployed to: (0x[0-9a-fA-F]{40})", result.stdout).group(1)
        log(f"Contract deployed to {contract}")

        # Backend.
        log("Starting backend")
        start(
            [str(BACKEND / ".venv" / "bin" / "uvicorn"), "app.main:app", "--port", "8001"],
            cwd=BACKEND,
            env_extra={
                "DATABASE_URL": TEST_DB,
                "CONTRACT_ADDRESS": contract,
                "RPC_URL": "http://127.0.0.1:8545",
                "UPLOAD_DIR": str(BACKEND / "uploads"),
            },
        )
        wait_for(f"{API}/health", name="backend")

        # Admin + issuer (DB + on-chain).
        status, admin = http("POST", f"{API}/auth/login",
                            {"email": "admin@demo.local", "password": "admin123"})
        assert status == 200, f"admin login failed: {admin}"
        admin_headers = {"Authorization": f"Bearer {admin['token']}"}
        status, issuer = http("POST", f"{API}/issuers", {
            "college_name": "Demo College", "wallet_address": ISSUER_WALLET,
            "email": "demo-issuer@demo.local", "password": "demo123"},
            headers=admin_headers)
        assert status == 201, f"issuer creation failed: {issuer}"
        issuer_id = issuer["id"]
        status, _ = http("PATCH", f"{API}/issuers/{issuer_id}/authorize", headers=admin_headers)
        assert status == 200
        status, issuer_login = http("POST", f"{API}/auth/login",
                                   {"email": "demo-issuer@demo.local", "password": "demo123"})
        assert status == 200
        issuer_headers = {"Authorization": f"Bearer {issuer_login['token']}"}
        out = run_hardhat_script({"MODE": "authorize", "CONTRACT_ADDRESS": contract})
        assert out["issuer"].lower() == ISSUER_WALLET.lower()
        log("Issuer authorized in database and on-chain")

        # --- Case 1: Register 10 certificates. ---
        pdf_paths = make_pdfs()
        log(f"Generated {len(pdf_paths)} synthetic PDFs in {CERTS_DIR}")
        for (name, course, issue_date), pdf_path in zip(STUDENTS, pdf_paths):
            pdf_bytes = pdf_path.read_bytes()
            status, cert = http("POST", f"{API}/certificates", data={
                "student_name": name, "course": course, "college": "Demo College",
                "issue_date": issue_date, "issuer_id": str(issuer_id),
            }, files={"file": (pdf_path.name, pdf_bytes, "application/pdf")},
                headers=issuer_headers)
            assert status == 201, f"upload failed for {name}: {cert}"
            out = run_hardhat_script({
                "MODE": "register", "CONTRACT_ADDRESS": contract,
                "CERT_ID": cert["certificate_id"], "CERT_HASH": cert["sha256_hash"]})
            assert out["status"] == 1
            status, confirmed = http("POST",
                f"{API}/certificates/{cert['certificate_id']}/confirm-blockchain",
                {"transaction_hash": out["tx_hash"]}, headers=issuer_headers)
            assert status == 200 and confirmed["blockchain_status"] == "ACTIVE"
            registered.append({
                "student": name, "course": course,
                "certificate_id": cert["certificate_id"],
                "sha256_hash": cert["sha256_hash"],
                "tx_hash": out["tx_hash"], "status": "ACTIVE",
                "pdf_path": str(pdf_path),
            })
            log(f"Registered {cert['certificate_id']} for {name}")
        record("Case 1: Register 10 certificates", "10 ACTIVE",
               f"{len(registered)} ACTIVE", len(registered) == 10,
               f"IDs: {', '.join(r['certificate_id'] for r in registered)}")

        # --- Case 2: Upload an original certificate -> VALID. ---
        first = registered[0]
        status, ver = http("POST", f"{API}/verify",
                           files={"file": ("certificate.pdf", Path(first["pdf_path"]).read_bytes(), "application/pdf")})
        record("Case 2: Original certificate", "VALID",
               ver.get("verification_result"), ver.get("verification_result") == "VALID",
               f"Certificate {first['certificate_id']}, no ID supplied (fingerprint lookup)")

        # --- Case 3: Modify one byte and upload it -> MODIFIED. ---
        original_bytes = Path(first["pdf_path"]).read_bytes()
        name_bytes = first["student"].encode()
        idx = original_bytes.index(name_bytes)
        modified_bytes = bytearray(original_bytes)
        modified_bytes[idx] = ord("X") if original_bytes[idx] != ord("X") else ord("Y")
        modified_bytes = bytes(modified_bytes)
        differing = [i for i, (a, b) in enumerate(zip(original_bytes, modified_bytes)) if a != b]
        assert len(differing) == 1 and len(modified_bytes) == len(original_bytes), \
            f"modified file must differ in exactly 1 byte, got {len(differing)}"
        assert modified_bytes.startswith(b"%PDF")
        modified_path = CERTS_DIR / "cert-01-modified.pdf"
        modified_path.write_bytes(modified_bytes)
        status, ver = http("POST", f"{API}/verify",
                           data={"certificate_id": first["certificate_id"]},
                           files={"file": ("certificate.pdf", modified_bytes, "application/pdf")})
        record("Case 3: Modified certificate (1 byte, with ID)", "MODIFIED",
               ver.get("verification_result"), ver.get("verification_result") == "MODIFIED",
               f"Byte {differing[0]} changed ({original_bytes[differing[0]]} -> {modified_bytes[differing[0]]}), "
               f"Certificate {first['certificate_id']}. Without an ID this would be NOT_FOUND (Phase 5 finding).")

        # --- Case 4: Revoke one certificate -> REVOKED. ---
        second = registered[1]
        out = run_hardhat_script({
            "MODE": "revoke", "CONTRACT_ADDRESS": contract, "CERT_ID": second["certificate_id"]})
        assert out["status"] == 1
        status, confirmed = http("POST",
            f"{API}/certificates/{second['certificate_id']}/confirm-revocation",
            {"transaction_hash": out["tx_hash"]}, headers=issuer_headers)
        assert status == 200 and confirmed["blockchain_status"] == "REVOKED"
        second["status"] = "REVOKED"
        second["revoke_tx_hash"] = out["tx_hash"]
        status, ver = http("POST", f"{API}/verify",
                           data={"certificate_id": second["certificate_id"]},
                           files={"file": ("certificate.pdf", Path(second["pdf_path"]).read_bytes(), "application/pdf")})
        record("Case 4: Revoked certificate", "REVOKED",
               ver.get("verification_result"), ver.get("verification_result") == "REVOKED",
               f"Certificate {second['certificate_id']}, original file, after revocation")

        # --- Case 5: Search an unknown Certificate ID -> NOT FOUND. ---
        status, lookup = http("GET", f"{API}/certificates/CERT-UNKNOWN")
        get_404 = status == 404
        status, ver = http("POST", f"{API}/verify",
                           data={"certificate_id": "CERT-UNKNOWN"},
                           files={"file": ("certificate.pdf", Path(first["pdf_path"]).read_bytes(), "application/pdf")})
        record("Case 5: Unknown Certificate ID", "NOT FOUND (NOT_FOUND)",
               ver.get("verification_result"),
               get_404 and ver.get("verification_result") == "NOT_FOUND",
               "GET /certificates/CERT-UNKNOWN -> 404; /verify CERT-UNKNOWN -> NOT_FOUND. "
               "CERT-UNKNOWN was never registered.")

        # --- Case 6: Unauthorized issue attempt -> REJECTED (two real paths). ---
        status, pending = http("POST", f"{API}/issuers", {
            "college_name": "Pending College", "wallet_address": PENDING_WALLET,
            "email": "pending-issuer@demo.local", "password": "demo123"},
            headers=admin_headers)
        assert status == 201
        pending_id = pending["id"]  # deliberately NOT authorized in the database
        status, pending_login = http("POST", f"{API}/auth/login",
                                    {"email": "pending-issuer@demo.local", "password": "demo123"})
        pending_headers = {"Authorization": f"Bearer {pending_login['token']}"}
        status, attempt = http("POST", f"{API}/certificates", data={
            "student_name": "Unauthorized Student", "course": "BSc",
            "college": "Pending College", "issue_date": "2026-04-26",
            "issuer_id": str(pending_id),
        }, files={"file": ("certificate.pdf", Path(pdf_paths[0]).read_bytes(), "application/pdf")},
            headers=pending_headers)
        backend_rejected = status == 403
        dummy_hash = hashlib.sha256(b"unauthorized attempt").hexdigest()
        out = run_hardhat_script({
            "MODE": "register_unauthorized", "CONTRACT_ADDRESS": contract,
            "CERT_ID": "CERT-UNAUTH", "CERT_HASH": dummy_hash})
        contract_rejected = out.get("rejected") is True
        status, main_certs = http("GET", f"{API}/issuers/{issuer_id}/certificates", headers=issuer_headers)
        count_unchanged = status == 200 and len(main_certs) == 10
        record("Case 6: Unauthorized issue attempt", "REJECTED",
               f"backend={status if not backend_rejected else 403}, contract_rejected={contract_rejected}",
               backend_rejected and contract_rejected and count_unchanged,
               f"Backend upload by PENDING issuer -> 403; contract register by unauthorised wallet "
               f"({out.get('signer')}) -> rejected; main issuer still has 10 certificates.")

        # --- Case 7: Smart-contract permissions automatically. ---
        result = subprocess.run(
            ["npx", "hardhat", "test"], cwd=BLOCKCHAIN,
            capture_output=True, text=True, timeout=300,
        )
        passing_match = re.search(r"(\d+) passing", result.stdout)
        failing_match = re.search(r"(\d+) failing", result.stdout)
        passing = int(passing_match.group(1)) if passing_match else 0
        failing = int(failing_match.group(1)) if failing_match else 0
        record("Case 7: Smart-contract permissions (automated tests)", "11 passing, 0 failing",
               f"{passing} passing, {failing} failing",
               result.returncode == 0 and passing >= 11 and failing == 0,
               "npx hardhat test in blockchain/ (Phase 1 tests, including unauthorised register/revoke).")

        # Extra: QR link check (Phase 5) — QR URL opens the same record.
        status, record_qr = http("GET", f"{API}/certificates/{first['certificate_id']}")
        record("Extra: QR link (verify?id=...) opens the record", "Record Found",
               "Record Found" if status == 200 else f"HTTP {status}",
               status == 200 and record_qr["certificate_id"] == first["certificate_id"],
               f"Simulates scanning the QR code for {first['certificate_id']}.")

        # Verification history.
        status, logs = http("GET", f"{API}/verification-logs", headers=issuer_headers)
        results = {log["verification_result"] for log in logs} if status == 200 else set()
        history_ok = {"VALID", "MODIFIED", "REVOKED", "NOT_FOUND"} <= results
        record("Extra: Verification history contains all four results", "VALID, MODIFIED, REVOKED, NOT_FOUND",
               ", ".join(sorted(results)), history_ok,
               f"{len(logs) if status == 200 else 0} log rows in this demo run.")

        # Write the result log.
        all_pass = all(c["passed"] for c in cases)
        lines = []
        lines.append("# Demo Result — Blockchain-Based Academic Certificate Verification")
        lines.append("")
        lines.append(f"Run at (UTC): {started_at}")
        lines.append(f"Contract address (local Hardhat, this run only): {contract}")
        lines.append(f"Issuer wallet (Hardhat account 1): {ISSUER_WALLET}")
        lines.append(f"Issuer login (demo): demo-issuer@demo.local / demo123")
        lines.append(f"Admin login (demo): admin@demo.local / admin123")
        lines.append(f"Backend (this run): {API} — database: certificate_demo")
        lines.append("")
        lines.append(f"Overall: {'ALL CASES PASS' if all_pass else 'SOME CASES FAILED'} "
                    f"({sum(1 for c in cases if c['passed'])}/{len(cases)} pass)")
        lines.append("")
        lines.append("## Registered certificates (10 synthetic samples)")
        lines.append("")
        lines.append("| # | Student | Course | Certificate ID | SHA-256 (first 16) | Status | Transaction (first 16) |")
        lines.append("|---|---|---|---|---|---|---|")
        for i, r in enumerate(registered, start=1):
            lines.append(
                f"| {i} | {r['student']} | {r['course']} | {r['certificate_id']} | "
                f"{r['sha256_hash'][:16]}… | {r['status']} | {r['tx_hash'][:16]}… |"
            )
        lines.append("")
        lines.append("## Cases (notes, Section 19, in order)")
        lines.append("")
        for c in cases:
            lines.append(f"### {c['name']} — {'PASS' if c['passed'] else 'FAIL'}")
            lines.append(f"- Expected: {c['expected']}")
            lines.append(f"- Actual: {c['actual']}")
            if c["detail"]:
                lines.append(f"- Detail: {c['detail']}")
            lines.append("")
        lines.append("## Notes for the presenter")
        lines.append("")
        lines.append("- Certificate IDs and transaction hashes in this file are from "
                     "this run only. Re-running the demo generates new IDs (they are "
                     "random) and new transaction hashes (fresh local chain).")
        lines.append("- Case 3 supplies the Certificate ID, because a modified file's "
                     "new fingerprint alone cannot identify its original (Phase 5 finding).")
        lines.append("- Case 6 was attempted through real paths, not mocked: a real "
                     "backend 403 for a PENDING issuer, and a real contract revert "
                     "for an unauthorised wallet. No certificate was created by either attempt.")
        lines.append("- All 10 PDFs are synthetic samples, labelled as such inside "
                     "each PDF, in demo/certificates/. No real student data is used.")
        lines.append("- To show the same certificates in the frontend afterwards, "
                     "re-run with --keep-servers, then open the frontend (see demo/README.md).")
        (DEMO_DIR / "DEMO_RESULT.md").write_text("\n".join(lines) + "\n")
        log(f"Result log written to {DEMO_DIR / 'DEMO_RESULT.md'}")
        log(f"Overall: {'ALL CASES PASS' if all_pass else 'SOME CASES FAILED'}")

        if args.keep_servers:
            log("Keeping servers running: Hardhat node on :8545, backend on :8001.")
            log("Frontend: cd frontend && npm run dev (http://localhost:5173).")
            log("Set VITE_CONTRACT_ADDRESS in frontend/.env to the contract address above.")
            return 0 if all_pass else 1
        return 0 if all_pass else 1
    finally:
        if not args.keep_servers:
            stop_all()
        else:
            # Detach: do not kill the servers, but do not leave this
            # script's process list holding them either.
            processes.clear()


if __name__ == "__main__":
    sys.exit(main())
