pragma solidity >=0.4.0;

// We need this to persuade Truffle to compile all the code we want to use.

import "@ensdomains/ens/contracts/ENSRegistryWithFallback.sol";
import "@ensdomains/ens/contracts/ReverseRegistrar.sol";
import "@ensdomains/resolver/contracts/PublicResolver.sol";
import "@ensdomains/ethregistrar/contracts/BaseRegistrarImplementation.sol";
import "@ensdomains/ens/contracts/TestRegistrar.sol";
import "@ensdomains/resolver/contracts/OwnedResolver.sol";
import "@ensdomains/resolver/contracts/DefaultReverseResolver.sol";
