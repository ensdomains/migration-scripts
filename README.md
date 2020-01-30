# ENS Migration scripts

This repository contains Truffle migrations that deploy the new ENS registry and related contracts. They are designed to function on both local test networks, as well as all the public networks (testnets and mainnet).

## Usage

```
OWNER_KEY=... [DEPLOYMENT_KEY=...] [TARGET_ADDRESS=...] truffle migrate --network=n [--dry-run]
```

`OWNER_KEY` should be the hex-format private key of an Ethereum account on the target network. This account will be used to deploy the Migration contract, and on public test networks, is expected to be the key that owns the Root contract or ENS root node; as part of step 4 this will be used to transfer ownership of .eth to the migration contract.

`DEPLOYMENT_KEY` should be the hex-format private key of an Ethereum account that will be used to deploy all other contracts. The purpose of using a separate key for this is to facilitate deterministic addresses for ENS contracts across different networks. If not supplied, defaults to `OWNER_KEY`.

`TARGET_ADDRESS` should be the Ethereum address to which ownership of all ownable ENS resources should be assigned at the end of migration. If not supplied, this defaults to the address of `OWNER_KEY`.

## Supported Networks

The following options are supported for the `--network` argument:

 - `development` - Deploys to a local development network, by first deploying the original ENS configuration, then deploys the migration on top of it. Does not deploy the DNSSEC or reverse registrars.
 - `test` - Generic test network instance. Intended to be run against an instance of ganache in fork mode for testing goerli or ropsten deployment.
 - `goerli`, `ropsten`, `rinkeby` - Deploys to the specified test network. `OWNER_KEY` must be the key that owns the root node on the specified network for migrations to complete successfully.
 - `mainnet` - Deploys to the Ethereum mainnet. Does not transfer ownership of the .eth node to the migration contract, as this can only be done via the ENS multisig; `OWNER_KEY` may be any funded Ethereum account.
 - `mainnet-test` - As with mainnet, but intended to be run against a local instance of ganache in fork mode.

## Migration Steps

 - Step 1 deploys the initial Truffle migration contract, required for Truffle's migration functionality.
 - Step 2 deploys the original ENS deployment - ENS registry, .eth registrar, and controller. This is only run on the `development` network.
 - Step 3 deploys the new ENS deployment. On the `development` network, it skips deploying the DNSSEC registrar or reverse registrar, but does deploy a .test registrar.
 - Step 4 activates the new deployment by transferring ownership of the .eth record to the migration contract. This step is skipped if the `OWNER_KEY` does not own the ENS root record or the root contract.
