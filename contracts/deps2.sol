pragma solidity >= 0.4.0;

// We need this to persuade Truffle to compile all the code we want to use.
// We need this second file because Solidity treats imports lexically, and
// without it we have conflicts between identically named imports.

import "@ensdomains/ethregistrar/contracts/ETHRegistrarController.sol";
import "@ensdomains/dnsregistrar/contracts/DNSRegistrar.sol";
import "@ensdomains/ethregistrar/contracts/SimplePriceOracle.sol";
