import { BrowserProvider, Contract, isAddress } from "ethers";
import abi from "../contract_abi.json";

// Phase 4 ethers.js write path. The issuer connects MetaMask, and the
// issuer's wallet sends register / revoke transactions, exactly as in
// blockchain/scripts/submit_tx.js (which proves the same calls without
// a browser). The backend then verifies the tx before marking ACTIVE
// or REVOKED (Phase 3 confirm endpoints) — the frontend never marks a
// certificate ACTIVE on its own.
//
// MetaMask setup for the local demo (see frontend README):
//   Network: Hardhat Local, RPC http://127.0.0.1:8545, Chain ID 31337
//   Import Hardhat account 1 (the authorised issuer in the demo).
//   Those are Hardhat's public local-test accounts, never real funds.

const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS || "";

export function contractAddress() {
  return CONTRACT_ADDRESS;
}

export function isBlockchainConfigured() {
  return Boolean(CONTRACT_ADDRESS) && isAddress(CONTRACT_ADDRESS);
}

async function getContract() {
  if (!isBlockchainConfigured()) {
    throw new Error(
      "Contract address is not configured. Set VITE_CONTRACT_ADDRESS in frontend/.env (from the deploy output) and restart the frontend."
    );
  }
  if (!window.ethereum) {
    throw new Error(
      "MetaMask is not installed. Install MetaMask, add the Hardhat local network (RPC http://127.0.0.1:8545, Chain ID 31337), and import the authorised issuer's Hardhat account. Or register via blockchain/scripts/submit_tx.js and paste the transaction hash into the Confirm step instead."
    );
  }
  const provider = new BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  return { contract: new Contract(CONTRACT_ADDRESS, abi, signer), signer };
}

export async function connectWallet() {
  if (!window.ethereum) throw new Error("MetaMask is not installed.");
  const provider = new BrowserProvider(window.ethereum);
  await provider.send("eth_requestAccounts", []);
  const signer = await provider.getSigner();
  return signer.getAddress();
}

export async function registerOnChain(certId, sha256Hex) {
  const { contract } = await getContract();
  const tx = await contract.registerCertificate(certId, `0x${sha256Hex}`);
  const receipt = await tx.wait();
  if (receipt.status !== 1) throw new Error("Register transaction failed on-chain.");
  return tx.hash;
}

export async function revokeOnChain(certId) {
  const { contract } = await getContract();
  const tx = await contract.revokeCertificate(certId);
  const receipt = await tx.wait();
  if (receipt.status !== 1) throw new Error("Revoke transaction failed on-chain.");
  return tx.hash;
}
