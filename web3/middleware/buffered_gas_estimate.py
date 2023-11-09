from typing import (
    TYPE_CHECKING,
    Any,
)

from eth_utils.toolz import (
    assoc,
)

from web3._utils.async_transactions import (
    get_buffered_gas_estimate as async_get_buffered_gas_estimate,
)
from web3._utils.transactions import (
    get_buffered_gas_estimate,
)
from web3.middleware import Web3Middleware
from web3.types import (
    RPCEndpoint,
)

if TYPE_CHECKING:
    from web3.main import (  # noqa: F401
        AsyncWeb3,
        Web3,
    )


class BufferedGasEstimateMiddleware(Web3Middleware):
    """
    Includes a gas estimate for all transactions that do not already have a gas value.
    """

    def request_processor(self, w3: "Web3", method: "RPCEndpoint", params: Any) -> Any:
        if method == "eth_sendTransaction":
            transaction = params[0]
            if "gas" not in transaction:
                transaction = assoc(
                    transaction,
                    "gas",
                    hex(get_buffered_gas_estimate(w3, transaction)),
                )
                params = (transaction,)
        return params

    # -- async -- #

    async def async_request_processor(
        self, async_w3: "AsyncWeb3", method: "RPCEndpoint", params: Any
    ) -> Any:
        if method == "eth_sendTransaction":
            transaction = params[0]
            if "gas" not in transaction:
                gas_estimate = await async_get_buffered_gas_estimate(
                    async_w3, transaction
                )
                transaction = assoc(transaction, "gas", hex(gas_estimate))
                params = (transaction,)
        return params


buffered_gas_estimate_middleware = BufferedGasEstimateMiddleware()
