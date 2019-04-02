from eth_utils import (
    is_checksum_address,
)

from web3._utils.toolz import (
    assoc,
)
from web3.module import (
    Module,
    ModuleV2,
)
from web3.personal import (
    ecRecover,
    importRawKey,
    listAccounts,
    newAccount,
    sendTransaction,
    sign,
    unlockAccount,
)
from web3.shh import (
    addPrivateKey,
    addSymKey,
    deleteKey,
    deleteMessageFilter,
    getFilterMessages,
    getPrivateKey,
    getPublicKey,
    getSymKey,
    info,
    newKeyPair,
    newMessageFilter,
    newSymKey,
    post,
    subscribe,
    unsubscribe,
)


class ParityShh(ModuleV2):
    """
    https://wiki.parity.io/JSONRPC-shh-module
    """
    info = info
    newKeyPair = newKeyPair
    addPrivateKey = addPrivateKey
    newSymKey = newSymKey
    addSymKey = addSymKey
    getPublicKey = getPublicKey
    getPrivateKey = getPrivateKey
    getSymKey = getSymKey
    post = post
    newMessageFilter = newMessageFilter
    deleteMessageFilter = deleteMessageFilter
    getFilterMessages = getFilterMessages
    deleteKey = deleteKey
    subscribe = subscribe
    unsubscribe = unsubscribe


class ParityPersonal(ModuleV2):
    """
    https://wiki.parity.io/JSONRPC-personal-module
    """
    ecRecover = ecRecover
    importRawKey = importRawKey
    listAccounts = listAccounts
    newAccount = newAccount
    sendTransaction = sendTransaction
    sign = sign
    unlockAccount = unlockAccount


class Parity(Module):
    """
    https://paritytech.github.io/wiki/JSONRPC-parity-module
    """
    defaultBlock = "latest"

    def enode(self):
        return self.web3.manager.request_blocking(
            "parity_enode",
            [],
        )

    def listStorageKeys(self, address, quantity, hash_, block_identifier=None):
        if block_identifier is None:
            block_identifier = self.defaultBlock
        return self.web3.manager.request_blocking(
            "parity_listStorageKeys",
            [address, quantity, hash_, block_identifier],
        )

    def netPeers(self):
        return self.web3.manager.request_blocking(
            "parity_netPeers",
            [],
        )

    def traceReplayTransaction(self, transaction_hash, mode=['trace']):
        return self.web3.manager.request_blocking(
            "trace_replayTransaction",
            [transaction_hash, mode],
        )

    def traceReplayBlockTransactions(self, block_identifier, mode=['trace']):
        return self.web3.manager.request_blocking(
            "trace_replayBlockTransactions",
            [block_identifier, mode]
        )

    def traceBlock(self, block_identifier):
        return self.web3.manager.request_blocking(
            "trace_block",
            [block_identifier]
        )

    def traceFilter(self, params):
        return self.web3.manager.request_blocking(
            "trace_filter",
            [params]
        )

    def traceTransaction(self, transaction_hash):
        return self.web3.manager.request_blocking(
            "trace_transaction",
            [transaction_hash]
        )

    def traceCall(self, transaction, mode=['trace'], block_identifier=None):
        # TODO: move to middleware
        if 'from' not in transaction and is_checksum_address(self.defaultAccount):
            transaction = assoc(transaction, 'from', self.defaultAccount)

        # TODO: move to middleware
        if block_identifier is None:
            block_identifier = self.defaultBlock
        return self.web3.manager.request_blocking(
            "trace_call",
            [transaction, mode, block_identifier],
        )

    def traceRawTransaction(self, raw_transaction, mode=['trace']):
        return self.web3.manager.request_blocking(
            "trace_rawTransaction",
            [raw_transaction, mode],
        )
