const ENSRegistry = artifacts.require('@ensdomains/ens/ENSRegistry');
const EthRegistrarSubdomainRegistrar = artifacts.require("EthRegistrarSubdomainRegistrar");
const HashRegistrar = artifacts.require('@ensdomains/ens/HashRegistrar');
const OldBaseRegistrar = artifacts.require('./OldBaseRegistrarImplementation');
var Promise = require('bluebird');

const namehash = require('eth-ens-namehash');
const sha3 = require('web3-utils').sha3;
const toBN = require('web3-utils').toBN;

const DAYS = 24 * 60 * 60;
const SALT = sha3('foo');
const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const ETH_LABEL = sha3("eth");
const ETH_NODE = namehash.hash("eth");
const MIN_COMMITMENT_AGE = 60;
const MAX_COMMITMENT_AGE = 86400;

const advanceTime = Promise.promisify(function(delay, done) {
	web3.currentProvider.send({
		jsonrpc: "2.0",
		"method": "evm_increaseTime",
		params: [delay]}, done)
	}
);

async function registerOldNames(ens, hashRegistrar, names, finalisedNames, account) {
  var hashes = names.map(sha3);
  var value = toBN(10000000000000000);
  var bidHashes = await Promise.map(hashes, (hash) => hashRegistrar.shaBid(hash, account, value, SALT));
  await hashRegistrar.startAuctions(hashes);
  await Promise.map(bidHashes, (h) => hashRegistrar.newBid(h, {value: value, from: account}));
  await advanceTime(3 * DAYS + 1);
  await Promise.map(hashes, (hash) => hashRegistrar.unsealBid(hash, value, SALT, {from: account}));
  await advanceTime(2 * DAYS + 1);
  await Promise.map(finalisedNames.map(sha3), (hash) => hashRegistrar.finalizeAuction(hash, {from: account}));
}

// Development network only: Deploy the old ENS contracts with some sample names.
module.exports = async function(deployer, network, accounts) {
  if(network !== 'development') return;

  // Deploy the registry
  await deployer.deploy(ENSRegistry, {from: accounts[0]});
  const ens = await ENSRegistry.deployed();
  await deployer.deploy(HashRegistrar, ENSRegistry.address, ETH_NODE, 1493895600);
  const hashRegistrar = await HashRegistrar.deployed();

  // Deploy the auction registrar and register some names
  await ens.setSubnodeOwner('0x0', ETH_LABEL, HashRegistrar.address, {from: accounts[0]});
  await registerOldNames(ens, hashRegistrar, ['oldname', 'migratename', 'nonfinalname'], ['oldname', 'migratename'], accounts[0]);

  // Create the original 'permanent' registrar and register some names on it
  transferPeriodEnds = (await web3.eth.getBlock('latest')).timestamp + 365 * DAYS;
  await deployer.deploy(OldBaseRegistrar, ens.address, hashRegistrar.address, ETH_NODE, transferPeriodEnds, {from: accounts[0]});
  await advanceTime(28 * DAYS + 1);  // Fast forward past the migration lock period
  oldRegistrar = await OldBaseRegistrar.deployed();
  await oldRegistrar.addController(accounts[0], {from: accounts[0]});
  await ens.setSubnodeOwner('0x0', ETH_LABEL, oldRegistrar.address, {from: accounts[0]});
  await Promise.map(["name", "name2"].map(sha3), (label) => oldRegistrar.register(label, accounts[0], 86400, {from: accounts[0]}));

  // Migrate oldname to the original 'permanent' registrar
  await hashRegistrar.transferRegistrars(sha3('migratename'), {from: accounts[0]});

	// Deploy a subdomain registrar
	await deployer.deploy(EthRegistrarSubdomainRegistrar, ens.address);
}
