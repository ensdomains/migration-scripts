const ENSRegistry = artifacts.require('@ensdomains/ens/ENSRegistry');
const ENSRegistryWithFallback = artifacts.require('@ensdomains/ens/ENSRegistryWithFallback');
const ENSMigrationSubdomainRegistrar = artifacts.require("@ensdomains/subdomain-registrar/ENSMigrationSubdomainRegistrar");
const EthRegistrarSubdomainRegistrar = artifacts.require("@ensdomains/subdomain-registrar/EthRegistrarSubdomainRegistrar");
const OwnedResolver = artifacts.require('@ensdomains/resolver/OwnedResolver');
const SimplePriceOracle = artifacts.require('@ensdomains/ethregistrar/contracts/SimplePriceOracle');
const ReverseRegistrar = artifacts.require('@ensdomains/ens/ReverseRegistrar');
const BaseRegistrarImplementation = artifacts.require('@ensdomains/ethregistrar/BaseRegistrarImplementation');
const RegistrarMigration = artifacts.require('@ensdomains/ethregistrar/RegistrarMigration');
const TestRegistrar = artifacts.require('@ensdomains/ens/TestRegistrar');
const DefaultReverseResolver = artifacts.require('@ensdomains/resolver/DefaultReverseResolver');
const PublicResolver = artifacts.require('@ensdomains/resolver/PublicResolver');
const ETHRegistrarController = artifacts.require('@ensdomains/ethregistrar/ETHRegistrarController');
const DNSRegistrar = artifacts.require('@ensdomains/dnsregistrar/DNSRegistrar');
const Root = artifacts.require('@ensdomains/root/Root');

const namehash = require('eth-ens-namehash');
const sha3 = require('web3-utils').sha3;

const config = require('../ens-config.js');

module.exports = async function(deployer, network, accounts) {
  const registryAddress = network=='development'?ENSRegistry.address:config.REGISTRIES[network];
  const oldENS = await ENSRegistryWithFallback.at(registryAddress);
  const oldRegistrar = await oldENS.owner(config.ETH_NODE);
  const oldSubdomainRegistrar = network=='development'?EthRegistrarSubdomainRegistrar.address:(config.SUBDOMAIN_REGISTRARS[network] || config.ZERO_ADDRESS);

  // Deploy the registry
  await deployer.deploy(ENSRegistryWithFallback, registryAddress, {from: accounts[1]});
  const ens = await ENSRegistryWithFallback.deployed();

  // Deploy a new public resolver
  await deployer.deploy(PublicResolver, ENSRegistryWithFallback.address, {from: accounts[1]});

  // Deploy the OwnedResolver for .eth
  await deployer.deploy(OwnedResolver);
  const ownedResolver = await OwnedResolver.deployed();

  // Deploy and activate the .eth registrar
  await deployer.deploy(BaseRegistrarImplementation, ENSRegistryWithFallback.address, config.ETH_NODE, {from: accounts[1]});
  const registrar = await BaseRegistrarImplementation.deployed();
  await ens.setSubnodeRecord(config.ZERO_ADDRESS, config.ETH_LABEL, BaseRegistrarImplementation.address, ownedResolver.address, 0, {from: accounts[1]});

  // Register 'migrated.eth' and configure a resolved address so people can check easily if their wallet is migrated
  await registrar.addController(accounts[1], {from: accounts[1]});
  await registrar.register(sha3('migrated'), accounts[0], 31536000, {from: accounts[1]});
  await ens.setResolver(namehash.hash('migrated.eth'), ownedResolver.address, {from: accounts[0]});
  await ownedResolver.methods['setAddr(bytes32,address)'](namehash.hash('migrated.eth'), config.TARGET_ADDRESS || accounts[0]);
  await registrar.removeController(accounts[1], {from: accounts[1]});

  // Deploy a new subdomain registrar
  await deployer.deploy(ENSMigrationSubdomainRegistrar, ens.address, {from: accounts[1], gas: 4000000});

  // Deploy the migration contract and enable it as a registrar controller
  await deployer.deploy(
    RegistrarMigration,
    oldRegistrar,
    await registrar.address,
    oldSubdomainRegistrar,
    ENSMigrationSubdomainRegistrar.address,
    {from: accounts[1], gas: 3000000});
  await registrar.addController(RegistrarMigration.address, {from: accounts[1]});

  // Deploy - but don't activate - the standard controller
  let priceOracle = config.PRICE_ORACLES[network];
  if(priceOracle === undefined && !network.startsWith('mainnet')) {
    await deployer.deploy(SimplePriceOracle, 1);
    priceOracle = SimplePriceOracle.address;
  }
  await deployer.deploy(ETHRegistrarController, BaseRegistrarImplementation.address, priceOracle, config.MIN_COMMITMENT_AGE, config.MAX_COMMITMENT_AGE, {from: accounts[1]});
  const registrarController = await ETHRegistrarController.deployed();

  // Configure the owned resolver
  await ownedResolver.methods['setAddr(bytes32,address)'](config.ETH_NODE, BaseRegistrarImplementation.address);
  await ownedResolver.setInterface(config.ETH_NODE, "0x6ccb2df4", BaseRegistrarImplementation.address); // Legacy wrong ERC721 ID
  await ownedResolver.setInterface(config.ETH_NODE, "0x80ac58cd", BaseRegistrarImplementation.address); // Correct ERC721 ID
  await ownedResolver.setInterface(config.ETH_NODE, "0x018fac06", ETHRegistrarController.address); // Controller interface

  const ownerAddress = config.TARGET_ADDRESS || accounts[0];

  if(!network.startsWith("mainnet")) {
      // Deploy the test registrar
      await deployer.deploy(TestRegistrar, ens.address, namehash.hash('test'));
      await ens.setSubnodeOwner(config.ZERO_ADDRESS, sha3('test'), TestRegistrar.address, {from: accounts[1]});
  }

  // None of the last steps apply to a local development instance.
  if(network != 'development') {
      // Deploy and activate the reverse registrar
      await deployer.deploy(DefaultReverseResolver, ENSRegistryWithFallback.address, {from: accounts[1], gas: 1000000});
      await deployer.deploy(ReverseRegistrar, ENSRegistryWithFallback.address, DefaultReverseResolver.address, {from: accounts[1], gas: 1000000});
      await ens.setSubnodeOwner(config.ZERO_ADDRESS, sha3("reverse"), accounts[1], {from: accounts[1]});
      await ens.setSubnodeOwner(namehash.hash("reverse"), sha3("addr"), ReverseRegistrar.address, {from: accounts[1]});
      await ens.setOwner(namehash.hash("reverse"), config.ZERO_ADDRESS, {from: accounts[1]});

      // Deploy the DNS registrar and configure it for .xyz
      const oldXyzRegistrarAddress = await oldENS.owner(namehash.hash("xyz"));
      if(oldXyzRegistrarAddress != config.ZERO_ADDRESS) {
          const oldXyzRegistrar = await DNSRegistrar.at(oldXyzRegistrarAddress);
          await deployer.deploy(DNSRegistrar, await oldXyzRegistrar.oracle(), ENSRegistryWithFallback.address, {from: accounts[1]});
          await ens.setSubnodeOwner(config.ZERO_ADDRESS, sha3("xyz"), DNSRegistrar.address, {from: accounts[1]});
      }

      // Deploy the root contract and make it the owner of the root node
      await deployer.deploy(Root, ENSRegistryWithFallback.address, {from: accounts[1]});
      const root = await Root.deployed();
      await ens.setOwner(config.ZERO_ADDRESS, Root.address, {from: accounts[1]});

      // Transfer ownership of the root to the required account
      await root.setController(ownerAddress, true, {from: accounts[1]});
      await root.transferOwnership(ownerAddress, {from: accounts[1]});
  }

  // Transfer ownership of the .eth registrar, and .eth registrat controller to the required account
  await registrar.transferOwnership(ownerAddress, {from: accounts[1]});
  await registrarController.transferOwnership(ownerAddress, {from: accounts[1]});
};
