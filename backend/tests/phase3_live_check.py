"""Phase 3 live end-to-end check (NOT part of the pytest suite).

Proves the full split from the confirmed Phase 0 decision 2, for real:
  FastAPI upload -> ethers.js register tx -> backend confirm -> ACTIVE
  ethers.js revoke tx -> backend confirm -> REVOKED
  confirm without a tx -> rejected, status unchanged

Prerequisites: PostgreSQL running, Hardhat + backend dependencies installed.
This script starts its own Hardhat node (port 8545) and backend (port 8001)
and kills both on exit, even on failure. It uses the test database and
clears its tables first — never point it at real data.

Run from backend/:
  .venv/bin/python tests/phase3_live_check.py
"""

import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
BACKEND = ROOT / "backend"
BLOCKCHAIN = ROOT / "blockchain"
ISSUER_WALLET = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # Hardhat account 1
PDF = b"%PDF-1.4 phase3 live certificate"
TEST_DB = "postgresql+psycopg2://postgres:postgres@localhost:5432/cert_verify_test"

processes = []


def log(msg):
    print(f"[phase3] {msg}", flush=True)


def start(cmd, cwd, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        # Own process group, so cleanup kills the whole server tree
        # (Hardhat node otherwise survives a plain terminate).
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
                "http://127.0.0.1:8545",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    raise RuntimeError("Hardhat node did not become ready")


def http(method, url, data=None, files=None, headers=None):
    """Minimal HTTP helper using urllib (no extra dependency)."""
    import uuid

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
        req = urllib.request.Request(
            url, data=b"".join(parts), method=method, headers=hdrs,
        )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
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
    # The script's last line is always a JSON object.
    last_json = result.stdout.strip().splitlines()[-1]
    return json.loads(last_json)


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    log(f"OK: {message}")


def main():
    api = "http://127.0.0.1:8001"
    try:
        # 1. Clear the test database tables.
        log("Clearing test database tables")
        subprocess.run(
            [sys.executable, "-c",
             "from app.database import SessionLocal; "
             "from app.models import CertificateMetadata, Issuer, VerificationLog; "
             "db = SessionLocal(); "
             "db.query(VerificationLog).delete(); "
             "db.query(CertificateMetadata).delete(); "
             "db.query(Issuer).delete(); db.commit()"],
            cwd=BACKEND, check=True,
            env={**os.environ, "DATABASE_URL": TEST_DB},
        )

        # 2. Hardhat node + deploy.
        log("Starting Hardhat node")
        start(["npx", "hardhat", "node"], cwd=BLOCKCHAIN)
        wait_for_rpc()
        log("Deploying contract")
        result = subprocess.run(
            ["npx", "hardhat", "run", "scripts/deploy.js", "--network", "localhost"],
            cwd=BLOCKCHAIN, capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"deploy failed:\n{result.stdout}\n{result.stderr}")
        match = re.search(r"deployed to: (0x[0-9a-fA-F]{40})", result.stdout)
        contract = match.group(1)
        log(f"Contract deployed to {contract}")

        # 3. Backend, pointed at this contract.
        log("Starting backend")
        start(
            [str(BACKEND / ".venv" / "bin" / "uvicorn"),
             "app.main:app", "--port", "8001"],
            cwd=BACKEND,
            env_extra={
                "DATABASE_URL": TEST_DB,
                "CONTRACT_ADDRESS": contract,
                "RPC_URL": "http://127.0.0.1:8545",
                "UPLOAD_DIR": str(BACKEND / "tests" / "test_uploads"),
            },
        )
        wait_for(f"{api}/health", name="backend")
        status, body = http("GET", f"{api}/blockchain/status")
        check(status == 200 and body.get("configured") is True,
              f"blockchain status configured (chain_id={body.get('chain_id')})")

        # 4. Issuer in DB + authorized in DB + authorized on-chain.
        status, admin = http("POST", f"{api}/auth/login",
                            {"email": "admin@demo.local", "password": "admin123"})
        check(status == 200, "admin login works")
        admin_headers = {"Authorization": f"Bearer {admin['token']}"}
        status, issuer = http("POST", f"{api}/issuers", {
            "college_name": "Test College", "wallet_address": ISSUER_WALLET,
            "email": "issuer-live@test.local", "password": "issuer123"},
            headers=admin_headers)
        check(status == 201, "issuer created in database")
        issuer_id = issuer["id"]
        status, _ = http("PATCH", f"{api}/issuers/{issuer_id}/authorize",
                         headers=admin_headers)
        check(status == 200, "issuer authorized in database")
        status, issuer_login = http("POST", f"{api}/auth/login",
                                   {"email": "issuer-live@test.local",
                                    "password": "issuer123"})
        check(status == 200, "issuer login works")
        issuer_headers = {"Authorization": f"Bearer {issuer_login['token']}"}
        out = run_hardhat_script({"MODE": "authorize", "CONTRACT_ADDRESS": contract})
        check(out["issuer"].lower() == ISSUER_WALLET.lower(),
              f"issuer authorized on-chain (tx {out['tx_hash']})")

        # 5. Upload -> backend returns ID + SHA-256, NOT on-chain yet.
        status, cert = http("POST", f"{api}/certificates", data={
            "student_name": "Test Student", "course": "BSc",
            "college": "Test College", "issue_date": "2026-05-01",
            "issuer_id": str(issuer_id),
        }, files={"file": ("certificate.pdf", PDF, "application/pdf")},
           headers=issuer_headers)
        check(status == 201, "certificate uploaded")
        cert_id, cert_hash = cert["certificate_id"], cert["sha256_hash"]
        check(cert["blockchain_status"] == "NOT_REGISTERED_ONCHAIN",
              f"uploaded cert {cert_id} is NOT on-chain yet")

        # 6. Confirming without a transaction must fail.
        status, body = http("POST", f"{api}/certificates/{cert_id}/confirm-blockchain",
                            {"transaction_hash": "0x" + "00" * 32},
                            headers=issuer_headers)
        check(status == 409, "confirm without a real tx is rejected (409)")

        # 7. ethers.js register tx -> backend confirm -> ACTIVE.
        out = run_hardhat_script({
            "MODE": "register", "CONTRACT_ADDRESS": contract,
            "CERT_ID": cert_id, "CERT_HASH": cert_hash})
        check(out["status"] == 1, f"register tx mined ({out['tx_hash']})")
        status, cert = http("POST", f"{api}/certificates/{cert_id}/confirm-blockchain",
                            {"transaction_hash": out["tx_hash"]},
                            headers=issuer_headers)
        check(status == 200 and cert["blockchain_status"] == "ACTIVE",
              "backend confirm marks certificate ACTIVE")
        check(cert["blockchain_tx_hash"] == out["tx_hash"],
              "registration tx hash stored in database")

        # 8. Backend on-chain read matches the database record.
        status, onchain = http("GET", f"{api}/certificates/{cert_id}/blockchain")
        check(status == 200 and onchain["status"] == "ACTIVE"
              and onchain["hash"].lower() == ("0x" + cert_hash).lower()
              and onchain["issuer"].lower() == ISSUER_WALLET.lower(),
              "backend on-chain read matches ID + hash + issuer + ACTIVE")

        # 9. ethers.js revoke tx -> backend confirm -> REVOKED, record kept.
        out = run_hardhat_script({
            "MODE": "revoke", "CONTRACT_ADDRESS": contract, "CERT_ID": cert_id})
        check(out["status"] == 1, f"revoke tx mined ({out['tx_hash']})")
        status, cert = http("POST", f"{api}/certificates/{cert_id}/confirm-revocation",
                            {"transaction_hash": out["tx_hash"]},
                            headers=issuer_headers)
        check(status == 200 and cert["blockchain_status"] == "REVOKED",
              "backend confirm marks certificate REVOKED")
        status, onchain = http("GET", f"{api}/certificates/{cert_id}/blockchain")
        check(onchain["status"] == "REVOKED"
              and onchain["hash"].lower() == ("0x" + cert_hash).lower(),
              "revoked record is still readable on-chain with original hash")

        log("ALL PHASE 3 LIVE CHECKS PASSED")
    finally:
        stop_all()


if __name__ == "__main__":
    main()
