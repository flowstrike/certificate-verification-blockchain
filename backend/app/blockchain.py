"""Phase 3: backend blockchain verification (read-only).

The confirmed Phase 0 decision 2 splits the work like this:
- FastAPI validates, generates the ID, hashes the PDF, stores metadata.
- React + ethers.js (Phase 4) sends the register / revoke transaction.
  The ethers.js submit script in blockchain/scripts/submit_tx.js already
  proves that path today, before the React UI exists.
- This module NEVER sends a transaction. It only reads the contract
  (via web3.py) to verify that a transaction the frontend claims to
  have sent actually produced the expected on-chain record. Only then
  does the backend mark a certificate ACTIVE or REVOKED.

If CONTRACT_ADDRESS is not set, every function here raises
BlockchainNotConfigured instead of returning a fake result.
"""

import json

from web3 import Web3

from .config import CONTRACT_ABI_PATH, CONTRACT_ADDRESS, RPC_URL

# Contract Status enum (CertificateVerification.sol):
#   0 = None (no record), 1 = Active, 2 = Revoked
STATUS_NAMES = {0: "NOT_FOUND", 1: "ACTIVE", 2: "REVOKED"}


class BlockchainNotConfigured(Exception):
    pass


class BlockchainError(Exception):
    pass


def _web3() -> Web3:
    if not CONTRACT_ADDRESS:
        raise BlockchainNotConfigured(
            "CONTRACT_ADDRESS is not set. Deploy the contract first "
            "(blockchain/scripts/deploy.js) and set CONTRACT_ADDRESS."
        )
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise BlockchainError(f"Cannot reach blockchain RPC at {RPC_URL}")
    return w3


def _contract(w3: Web3):
    abi = json.loads(CONTRACT_ABI_PATH.read_text())
    return w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi
    )


def read_certificate(certificate_id: str) -> dict:
    """Read one on-chain record. Returns hash, issuer, status.

    Hash is returned as a 0x hex string so it can be compared directly
    with the backend's stored SHA-256 hex digest (with a 0x prefix).
    """
    w3 = _web3()
    contract = _contract(w3)
    cert_hash, issuer, status = contract.functions.getCertificateRecord(
        certificate_id
    ).call()
    return {
        "certificate_id": certificate_id,
        "hash": "0x" + cert_hash.hex(),
        "issuer": issuer,
        "status": STATUS_NAMES.get(status, "UNKNOWN"),
        "exists": status != 0,
    }


def is_issuer_authorized_onchain(wallet_address: str) -> bool:
    w3 = _web3()
    contract = _contract(w3)
    return bool(
        contract.functions.authorizedIssuers(
            Web3.to_checksum_address(wallet_address)
        ).call()
    )


def check_transaction(tx_hash: str) -> dict:
    """Check a transaction receipt: it must exist, have succeeded,
    and have been sent to this contract. Raises BlockchainError otherwise.
    """
    w3 = _web3()
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except Exception as exc:
        raise BlockchainError(f"Transaction not found: {tx_hash}") from exc
    if receipt is None:
        raise BlockchainError(f"Transaction not found: {tx_hash}")
    if receipt.get("status") != 1:
        raise BlockchainError(f"Transaction failed on-chain: {tx_hash}")
    to_address = receipt.get("to")
    if to_address and to_address.lower() != CONTRACT_ADDRESS.lower():
        raise BlockchainError(
            f"Transaction was not sent to this contract: {tx_hash}"
        )
    return {"transaction_hash": tx_hash, "status": "mined"}


def blockchain_status() -> dict:
    """Connection info for the Transaction Status view (Phase 4)."""
    if not CONTRACT_ADDRESS:
        return {"configured": False, "rpc_url": RPC_URL, "contract_address": None}
    w3 = _web3()
    return {
        "configured": True,
        "rpc_url": RPC_URL,
        "contract_address": CONTRACT_ADDRESS,
        "chain_id": w3.eth.chain_id,
    }
