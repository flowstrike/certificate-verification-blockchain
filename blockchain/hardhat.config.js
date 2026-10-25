require("@nomicfoundation/hardhat-toolbox");

// Phase 1: local Hardhat chain only (notes, Section 12).
// No mainnet, no real cryptocurrency.
module.exports = {
  solidity: "0.8.28",
  networks: {
    localhost: {
      url: "http://127.0.0.1:8545",
    },
  },
};
