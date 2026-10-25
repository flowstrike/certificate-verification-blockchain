import os
from pathlib import Path

# Phase 2 settings. DATABASE_URL is read from the environment so the same
# code works on any machine with PostgreSQL installed; see README.md for
# the local setup steps. No credential is hard-coded here as a secret:
# the default below is a local-demo value only and must be overridden
# with DATABASE_URL for any shared machine.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/certificate_verification",
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Implementation safeguard, NOT a rule from the notes: reject absurdly
# large uploads so a bad request cannot fill the disk.
MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024

# Phase 3: blockchain connection (read-only from the backend's side).
# Writes (register / revoke) are sent by React + ethers.js in Phase 4,
# per the confirmed Phase 0 decision 2; the backend only reads the
# contract to verify a transaction before marking a certificate ACTIVE
# or REVOKED. CONTRACT_ADDRESS is set after deploying (Phase 1 deploy
# script prints it). If it is empty, blockchain endpoints return 503
# instead of pretending to verify anything.
RPC_URL = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
CONTRACT_ADDRESS = os.environ.get("CONTRACT_ADDRESS", "")
CONTRACT_ABI_PATH = Path(__file__).resolve().parent / "contract_abi.json"
