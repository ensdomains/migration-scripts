const namehash = require('eth-ens-namehash');
const sha3 = require('web3-utils').sha3;

const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const ETH_LABEL = sha3("eth");
const ETH_NODE = namehash.hash("eth");

// Old registry address for each network
const REGISTRIES = {
  mainnet: "0x314159265dd8dbb310642f98f50c066173c1259b",
  "mainnet-test": "0x314159265dd8dbb310642f98f50c066173c1259b",
  test: "0x112234455c3a32fd11230c42e7bccd4a84e02010",
  ropsten: "0x112234455c3a32fd11230c42e7bccd4a84e02010",
  goerli: "0x112234455c3a32fd11230c42e7bccd4a84e02010",
  rinkeby: "0xe7410170f87102df0055eb195163a03b7f2bff4a",
};

// Price oracle contract on each network
const PRICE_ORACLES = {
  mainnet: "0xb9d374d0fe3d8341155663fae31b7beae0ae233a",
  "mainnet-test": "0xb9d374d0fe3d8341155663fae31b7beae0ae233a",
  test: "0x04cd12453859f6c21fa268bf9ab4d7f81a25d543",
  ropsten: "0x04cd12453859f6c21fa268bf9ab4d7f81a25d543",
  rinkeby: "0x856fe428783c85909f9e986d4c264f8142571193",
  goerli: "0xe14174f6c7eb9bc03fbae5316d4fea72392a2e06"
};

// Subdomain registrar address on each network.
// If not supplied, defaults to none (eg, no migration will be performed).
const SUBDOMAIN_REGISTRARS = {
  mainnet: "0xc32659651d137a18b79925449722855aa327231d",
  "mainnet-test": "0xc32659651d137a18b79925449722855aa327231d",
};

const MIN_COMMITMENT_AGE = 60;
const MAX_COMMITMENT_AGE = 86400;

const DUMMY_KEY = "4470af80c129a94bb4b76a24bf5136065f67fe4d10ef7b9876fde7ee10aad225";

const OWNER_KEY = process.env.OWNER_KEY || DUMMY_KEY;
const DEPLOYMENT_KEY = process.env.DEPLOYMENT_KEY || OWNER_KEY;
const TARGET_ADDRESS = process.env.TARGET_ADDRESS;

function add_forks(list) {
  Object.keys(list).forEach((k) => { list[k + "-fork"] = list[k]; });
}

add_forks(REGISTRIES);
add_forks(PRICE_ORACLES);
add_forks(SUBDOMAIN_REGISTRARS);

module.exports = {
  ZERO_ADDRESS,
  ETH_LABEL,
  ETH_NODE,
  REGISTRIES,
  PRICE_ORACLES,
  SUBDOMAIN_REGISTRARS,
  OWNER_KEY,
  DEPLOYMENT_KEY,
  TARGET_ADDRESS,
  MIN_COMMITMENT_AGE,
  MAX_COMMITMENT_AGE
};
