const ENSRegistry = artifacts.require('@ensdomains/ens/ENSRegistry');
const RegistrarMigration = artifacts.require('@ensdomains/ethregistrar/RegistrarMigration');
const Root = artifacts.require('@ensdomains/root/Root');

const config = require('../ens-config.js');

module.exports = async function(deployer, network, accounts) {
    const ownerAddress = config.TARGET_ADDRESS || accounts[0];
    const registryAddress = network=='development'?ENSRegistry.address:config.REGISTRIES[network];
    const oldENS = await ENSRegistry.at(registryAddress);
    const rootNodeOwner = await oldENS.owner(config.ZERO_ADDRESS);
    if(rootNodeOwner == accounts[0]) {
        console.log("Account owns root node directly")
        await oldENS.setSubnodeOwner(config.ZERO_ADDRESS, config.ETH_LABEL, RegistrarMigration.address, {from: accounts[0]});
    } else {
        if(web3.eth.getCode(rootNodeOwner) != '0x') {
            // Root contract deployed on this network
            const root = await Root.at(rootNodeOwner);
            if((await root.owner()) != accounts[0]) {
              console.log("Cannot activate new deployment: OWNER_ADDRESS does not own root contract. Skipping.");
              return;
            }
            await root.setSubnodeOwner(config.ETH_LABEL, RegistrarMigration.address, {from: accounts[0]});
        } else {
          console.log("Cannot activate new deployment: OWNER_ADDRESS does not own root node. Skipping.");
        }
    }
}
