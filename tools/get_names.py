import argparse
from binascii import unhexlify
import csv
from ens.utils import label_to_hash
from eth_utils import remove_0x_prefix
from hexbytes import HexBytes
import itertools
import json
import logging
import os
import web3
from web3.auto import w3

"""
Extracts a list of ENS label hashes that have been registered on the .eth
registrar and outputs them on standard output.

Usage:

  WEB3_PROVIDER_URI=http://... python3 get_names.py 0x31415...

Provide the address of the ENS registry on the chain that you are querying. The
tool will use this to determine a list of registrars that have been used on .eth,
and query events from each for names that were registered there.
"""

ZERO_HASH = HexBytes('0000000000000000000000000000000000000000000000000000000000000000')

AUCTION_REGISTRAR_ABI = json.loads('''[{"constant":false,"inputs":[{"name":"_hash","type":"bytes32"}],"name":"releaseDeed","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"_hash","type":"bytes32"}],"name":"getAllowedTime","outputs":[{"name":"timestamp","type":"uint256"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"unhashedName","type":"string"}],"name":"invalidateName","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"hash","type":"bytes32"},{"name":"owner","type":"address"},{"name":"value","type":"uint256"},{"name":"salt","type":"bytes32"}],"name":"shaBid","outputs":[{"name":"sealedBid","type":"bytes32"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"bidder","type":"address"},{"name":"seal","type":"bytes32"}],"name":"cancelBid","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"_hash","type":"bytes32"}],"name":"entries","outputs":[{"name":"","type":"uint8"},{"name":"","type":"address"},{"name":"","type":"uint256"},{"name":"","type":"uint256"},{"name":"","type":"uint256"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"ens","outputs":[{"name":"","type":"address"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_hash","type":"bytes32"},{"name":"_value","type":"uint256"},{"name":"_salt","type":"bytes32"}],"name":"unsealBid","outputs":[],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_hash","type":"bytes32"}],"name":"transferRegistrars","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"},{"name":"","type":"bytes32"}],"name":"sealedBids","outputs":[{"name":"","type":"address"}],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"_hash","type":"bytes32"}],"name":"state","outputs":[{"name":"","type":"uint8"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_hash","type":"bytes32"},{"name":"newOwner","type":"address"}],"name":"transfer","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"_hash","type":"bytes32"},{"name":"_timestamp","type":"uint256"}],"name":"isAllowed","outputs":[{"name":"allowed","type":"bool"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_hash","type":"bytes32"}],"name":"finalizeAuction","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"registryStarted","outputs":[{"name":"","type":"uint256"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"launchLength","outputs":[{"name":"","type":"uint32"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"sealedBid","type":"bytes32"}],"name":"newBid","outputs":[],"payable":true,"type":"function"},{"constant":false,"inputs":[{"name":"labels","type":"bytes32[]"}],"name":"eraseNode","outputs":[],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_hashes","type":"bytes32[]"}],"name":"startAuctions","outputs":[],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"hash","type":"bytes32"},{"name":"deed","type":"address"},{"name":"registrationDate","type":"uint256"}],"name":"acceptRegistrarTransfer","outputs":[],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_hash","type":"bytes32"}],"name":"startAuction","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"rootNode","outputs":[{"name":"","type":"bytes32"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"hashes","type":"bytes32[]"},{"name":"sealedBid","type":"bytes32"}],"name":"startAuctionsAndBid","outputs":[],"payable":true,"type":"function"},{"inputs":[{"name":"_ens","type":"address"},{"name":"_rootNode","type":"bytes32"},{"name":"_startDate","type":"uint256"}],"payable":false,"type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"name":"hash","type":"bytes32"},{"indexed":false,"name":"registrationDate","type":"uint256"}],"name":"AuctionStarted","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"hash","type":"bytes32"},{"indexed":true,"name":"bidder","type":"address"},{"indexed":false,"name":"deposit","type":"uint256"}],"name":"NewBid","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"hash","type":"bytes32"},{"indexed":true,"name":"owner","type":"address"},{"indexed":false,"name":"value","type":"uint256"},{"indexed":false,"name":"status","type":"uint8"}],"name":"BidRevealed","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"hash","type":"bytes32"},{"indexed":true,"name":"owner","type":"address"},{"indexed":false,"name":"value","type":"uint256"},{"indexed":false,"name":"registrationDate","type":"uint256"}],"name":"HashRegistered","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"hash","type":"bytes32"},{"indexed":false,"name":"value","type":"uint256"}],"name":"HashReleased","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"hash","type":"bytes32"},{"indexed":true,"name":"name","type":"string"},{"indexed":false,"name":"value","type":"uint256"},{"indexed":false,"name":"registrationDate","type":"uint256"}],"name":"HashInvalidated","type":"event"}]''')

BASE_REGISTRAR_ABI = json.loads('''[{"constant":true,"inputs":[{"name":"interfaceID","type":"bytes4"}],"name":"supportsInterface","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"tokenId","type":"uint256"}],"name":"getApproved","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"to","type":"address"},{"name":"tokenId","type":"uint256"}],"name":"approve","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"from","type":"address"},{"name":"to","type":"address"},{"name":"tokenId","type":"uint256"}],"name":"transferFrom","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"id","type":"uint256"},{"name":"owner","type":"address"}],"name":"reclaim","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"ens","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"from","type":"address"},{"name":"to","type":"address"},{"name":"tokenId","type":"uint256"}],"name":"safeTransferFrom","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"transferPeriodEnds","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"resolver","type":"address"}],"name":"setResolver","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"tokenId","type":"uint256"}],"name":"ownerOf","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"MIGRATION_LOCK_PERIOD","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[],"name":"renounceOwnership","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"owner","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"isOwner","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"id","type":"uint256"}],"name":"available","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"to","type":"address"},{"name":"approved","type":"bool"}],"name":"setApprovalForAll","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"controller","type":"address"}],"name":"addController","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"previousRegistrar","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"from","type":"address"},{"name":"to","type":"address"},{"name":"tokenId","type":"uint256"},{"name":"_data","type":"bytes"}],"name":"safeTransferFrom","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"GRACE_PERIOD","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"id","type":"uint256"},{"name":"duration","type":"uint256"}],"name":"renew","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"id","type":"uint256"}],"name":"nameExpires","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"controllers","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"baseNode","outputs":[{"name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"owner","type":"address"},{"name":"operator","type":"address"}],"name":"isApprovedForAll","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"label","type":"bytes32"},{"name":"deed","type":"address"},{"name":"","type":"uint256"}],"name":"acceptRegistrarTransfer","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"controller","type":"address"}],"name":"removeController","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"id","type":"uint256"},{"name":"owner","type":"address"},{"name":"duration","type":"uint256"}],"name":"register","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"_ens","type":"address"},{"name":"_previousRegistrar","type":"address"},{"name":"_baseNode","type":"bytes32"},{"name":"_transferPeriodEnds","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"name":"controller","type":"address"}],"name":"ControllerAdded","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"controller","type":"address"}],"name":"ControllerRemoved","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"id","type":"uint256"},{"indexed":true,"name":"owner","type":"address"},{"indexed":false,"name":"expires","type":"uint256"}],"name":"NameMigrated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"id","type":"uint256"},{"indexed":true,"name":"owner","type":"address"},{"indexed":false,"name":"expires","type":"uint256"}],"name":"NameRegistered","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"id","type":"uint256"},{"indexed":false,"name":"expires","type":"uint256"}],"name":"NameRenewed","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"previousOwner","type":"address"},{"indexed":true,"name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":true,"name":"tokenId","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"approved","type":"address"},{"indexed":true,"name":"tokenId","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"operator","type":"address"},{"indexed":false,"name":"approved","type":"bool"}],"name":"ApprovalForAll","type":"event"}]''')

REGISTRY_ABI = json.loads('''[{"constant":true,"inputs":[{"name":"node","type":"bytes32"}],"name":"resolver","outputs":[{"name":"","type":"address"}],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"node","type":"bytes32"}],"name":"owner","outputs":[{"name":"","type":"address"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"node","type":"bytes32"},{"name":"label","type":"bytes32"},{"name":"owner","type":"address"}],"name":"setSubnodeOwner","outputs":[],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"node","type":"bytes32"},{"name":"ttl","type":"uint64"}],"name":"setTTL","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"node","type":"bytes32"}],"name":"ttl","outputs":[{"name":"","type":"uint64"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"node","type":"bytes32"},{"name":"resolver","type":"address"}],"name":"setResolver","outputs":[],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"node","type":"bytes32"},{"name":"owner","type":"address"}],"name":"setOwner","outputs":[],"payable":false,"type":"function"},{"anonymous":false,"inputs":[{"indexed":true,"name":"node","type":"bytes32"},{"indexed":false,"name":"owner","type":"address"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"node","type":"bytes32"},{"indexed":true,"name":"label","type":"bytes32"},{"indexed":false,"name":"owner","type":"address"}],"name":"NewOwner","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"node","type":"bytes32"},{"indexed":false,"name":"resolver","type":"address"}],"name":"NewResolver","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"node","type":"bytes32"},{"indexed":false,"name":"ttl","type":"uint64"}],"name":"NewTTL","type":"event"}]''')

SUBDOMAIN_REGISTRAR_ABI = json.loads('''[{"constant":true,"inputs":[{"name":"interfaceID","type":"bytes4"}],"name":"supportsInterface","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"pure","type":"function"},{"constant":true,"inputs":[{"name":"label","type":"bytes32"}],"name":"owner","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[],"name":"stop","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"migration","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"registrarOwner","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"registrar","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"label","type":"bytes32"},{"name":"subdomain","type":"string"}],"name":"query","outputs":[{"name":"domain","type":"string"},{"name":"price","type":"uint256"},{"name":"rent","type":"uint256"},{"name":"referralFeePPM","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"ens","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"label","type":"bytes32"},{"name":"subdomain","type":"string"},{"name":"_subdomainOwner","type":"address"},{"name":"referrer","type":"address"},{"name":"resolver","type":"address"}],"name":"register","outputs":[],"payable":true,"stateMutability":"payable","type":"function"},{"constant":false,"inputs":[{"name":"_migration","type":"address"}],"name":"setMigrationAddress","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"label","type":"bytes32"},{"name":"subdomain","type":"string"}],"name":"rentDue","outputs":[{"name":"timestamp","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"name","type":"string"},{"name":"resolver","type":"address"}],"name":"setResolver","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"stopped","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"TLD_NODE","outputs":[{"name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"name","type":"string"}],"name":"migrate","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"label","type":"bytes32"},{"name":"subdomain","type":"string"}],"name":"payRent","outputs":[],"payable":true,"stateMutability":"payable","type":"function"},{"constant":false,"inputs":[{"name":"name","type":"string"},{"name":"price","type":"uint256"},{"name":"referralFeePPM","type":"uint256"},{"name":"_owner","type":"address"},{"name":"_transfer","type":"address"}],"name":"configureDomainFor","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"name","type":"string"},{"name":"price","type":"uint256"},{"name":"referralFeePPM","type":"uint256"}],"name":"configureDomain","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"name","type":"string"}],"name":"unlistDomain","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"name","type":"string"},{"name":"newOwner","type":"address"}],"name":"transfer","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"ens","type":"address"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"name":"label","type":"bytes32"},{"indexed":false,"name":"name","type":"string"}],"name":"DomainTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"label","type":"bytes32"},{"indexed":true,"name":"oldOwner","type":"address"},{"indexed":true,"name":"newOwner","type":"address"}],"name":"OwnerChanged","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"label","type":"bytes32"}],"name":"DomainConfigured","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"label","type":"bytes32"}],"name":"DomainUnlisted","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"label","type":"bytes32"},{"indexed":false,"name":"subdomain","type":"string"},{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"referrer","type":"address"},{"indexed":false,"name":"price","type":"uint256"}],"name":"NewRegistration","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"label","type":"bytes32"},{"indexed":false,"name":"subdomain","type":"string"},{"indexed":false,"name":"amount","type":"uint256"},{"indexed":false,"name":"expirationDate","type":"uint256"}],"name":"RentPaid","type":"event"}]''')

logger = logging.getLogger('main')
logger.setLevel(logging.DEBUG)
w3.middleware_onion.add(web3.middleware.http_retry_request_middleware)

parser = argparse.ArgumentParser(description="Extract a list of .eth label hashes from onchain events")
parser.add_argument('--start', type=int, help="Start block", default=0)
parser.add_argument('--subdomains', action='store_true', default=False, help="Get subdomain labels instead of .eth labels")
parser.add_argument('registry', type=str, help="Registry address")
parser.add_argument('file', type=argparse.FileType('r+t'))

def get_logs_iter(event, argumentFilters=None, fromBlock=1, toBlock='latest', targetBatchSize=100, maxBlocks=1000, mixingFactor=0.05):
    if toBlock == 'latest':
        toBlock = w3.eth.blockNumber
    numBlocks = maxBlocks / 2
    while fromBlock < toBlock:
        endBlock = min(fromBlock + int(numBlocks), toBlock)
        logging.info("Fetching %d blocks of logs starting at %d for address %s…%s", numBlocks, fromBlock, event.address[:6], event.address[-4:])
        logs = event.getLogs(argument_filters=argumentFilters, fromBlock=fromBlock, toBlock=endBlock-1)
        for log in logs:
            yield log
        fromBlock = endBlock
        logsPerBlock = max(len(logs) / numBlocks, 2 / maxBlocks)
        numBlocks = min(maxBlocks, (1 - mixingFactor) * numBlocks + mixingFactor * targetBatchSize / logsPerBlock)


def get_registrars(ens):
    startBlock = None
    lastRegistrar = None
    for log in ens.events.NewOwner.getLogs(argument_filters={'node': ZERO_HASH, 'label': label_to_hash('eth')}, fromBlock=0, toBlock='latest'):
        if lastRegistrar is not None:
            yield (lastRegistrar, startBlock, int(log.blockNumber))
        auctionRegistrar = w3.eth.contract(abi=AUCTION_REGISTRAR_ABI, address=log.args.owner)
        try:
            auctionRegistrar.functions.entries(ZERO_HASH).call()
            lastRegistrar = auctionRegistrar
            logging.info("Auction registrar %s at block %d", log.args.owner, log.blockNumber)
        except (web3.exceptions.BadFunctionCallOutput, ValueError) as e:
            permanentRegistrar = w3.eth.contract(abi=BASE_REGISTRAR_ABI, address=log.args.owner)
            try:
                permanentRegistrar.functions.nameExpires(0).call()
                lastRegistrar = permanentRegistrar
                logging.info("Permanent registrar %s at %d", log.args.owner, log.blockNumber)
            except (web3.exceptions.BadFunctionCallOutput, ValueError) as e:
                logging.error("Unrecognised .eth registrar contract %s at block %d", log.args.owner, log.blockNumber)
                lastRegistrar = None
        startBlock = int(log.blockNumber)
    if lastRegistrar is not None:
        yield (lastRegistrar, startBlock, 'latest')


def get_auction_registrar_names(event, startBlock, endBlock):
    logging.info("Getting auction registrar names at %s from %d to %d", event.address, startBlock, endBlock)
    for log in get_logs_iter(event, fromBlock=startBlock, toBlock=endBlock):
        if log.args.status != 2: continue
        yield (log.args.hash.hex(),)


def get_permanent_registrar_names(event, startBlock, endBlock):
    logging.info("Getting permanent registrar names at %s from %d to %s", event.address, startBlock, endBlock)
    for log in get_logs_iter(event, fromBlock=startBlock, toBlock=endBlock):
        yield (log.args.id.to_bytes(32, byteorder='big').hex(),)


def uniq(it):
    seen = set()
    for item in it:
        if item not in seen:
            yield item
            seen.add(item)


def get_domains(start, registry):
    ens = w3.eth.contract(abi=REGISTRY_ABI, address=registry)
    filters = []
    for registrar, startBlock, endBlock in get_registrars(ens):
        startBlock = max(startBlock, start)
        if endBlock != 'latest' and startBlock > endBlock: continue
        try:
            filters.append(get_auction_registrar_names(registrar.events.BidRevealed, startBlock, endBlock))
        except web3.exceptions.MismatchedABI:
            try:
                filters.append(get_permanent_registrar_names(registrar.events.NameRegistered, startBlock, endBlock))
            except web3.exceptions.MismatchedABI:
                logging.error("Unrecognised registrar at address %s and block %d", registrar.address, startBlock)
    return itertools.chain(*filters)


def get_subdomains(start, registrarAddress):
    registrar = w3.eth.contract(abi=SUBDOMAIN_REGISTRAR_ABI, address=registrarAddress)
    for log in get_logs_iter(registrar.events.NewRegistration, fromBlock=start, toBlock='latest'):
        yield (log.args.label.hex(), log.args.subdomain)


def main(args):
    r = csv.reader(args.file)
    labels = set((tuple(row) for row in r))
    if args.subdomains:
        new_labels = get_subdomains(args.start, args.registry)
    else:
        new_labels = get_domains(args.start, args.registry)
    labels = uniq(itertools.chain(labels, new_labels))
    args.file.seek(0)
    w = csv.writer(args.file)
    for label in labels:
        w.writerow(label)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main(parser.parse_args())
