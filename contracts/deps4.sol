pragma solidity >= 0.4.0;

// We need this to persuade Truffle to compile all the code we want to use.
// We need this *fourth* file because Solidity treats imports lexically, and
// without it we have conflicts between identically named imports.

import "@ensdomains/root/contracts/Root.sol";
