const HDWalletProvider = require('@truffle/hdwallet-provider');
const config = require('./ens-config.js');
require('dotenv').config();

const privateKeys = [config.OWNER_KEY, config.DEPLOYMENT_KEY];

function keyProvider(keys, url) {
    return function() {
        return new HDWalletProvider(keys, url, 0, 2);
    }
}

module.exports = {
  networks: {
    "development": {
      network_id: "*",
      skipDryRun: true,
      host: "localhost",
      port: 8545
    },
    "test": {
      provider: keyProvider(privateKeys, "http://localhost:8545"),
      network_id: "*",
      skipDryRun: true
    },
    "mainnet": {
      provider: keyProvider(privateKeys, "https://mainnet.infura.io/v3/58a380d3ecd545b2b5b3dad5d2b18bf0"),
      network_id: "1",
      gasPrice: 2000000000,
    },
    "mainnet-test": {
      provider: keyProvider(privateKeys, "http://localhost:8545"),
      network_id: "1",
      skipDryRun: true,
      gasPrice: 1000000000,
    },
    "ropsten": {
      provider: keyProvider(privateKeys, "https://ropsten.infura.io/v3/58a380d3ecd545b2b5b3dad5d2b18bf0"),
      network_id: "3",
      gasPrice: 10000000000,
      skipDryRun: true,
    },
    "rinkeby": {
      provider: keyProvider(privateKeys, "https://rinkeby.infura.io/v3/58a380d3ecd545b2b5b3dad5d2b18bf0"),
      network_id: "4",
      gasPrice: 10000000000,
    },
    "goerli": {
      provider: keyProvider(privateKeys, "https://goerli.infura.io/v3/58a380d3ecd545b2b5b3dad5d2b18bf0"),
      network_id: "5",
      skipDryRun: true,
      gasPrice: 10000000000
    },
  },
  // Set default mocha options here, use special reporters etc.
  mocha: {
    // timeout: 100000
  },

  // Configure your compilers
  compilers: {
    solc: {
      //version: "0.5.8",    // Fetch exact version from solc-bin (default: truffle's version)
      // docker: true,        // Use "0.5.1" you've installed locally with docker (default: false)
      settings: {          // See the solidity docs for advice about optimization and evmVersion
       optimizer: {
         enabled: false,
         runs: 200
       }
      }
    }
  },
  plugins: [
    'truffle-plugin-verify',
  ],
  api_keys: {
    etherscan: process.env.ETHERSCAN_API_KEY
  }
}
