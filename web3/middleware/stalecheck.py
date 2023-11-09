import time
from typing import (  # noqa: F401
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Dict,
    Optional,
)

from web3.exceptions import (
    StaleBlockchain,
)
from web3.middleware import (
    Web3Middleware,
)
from web3.types import (
    AsyncMiddleware,
    AsyncMiddlewareCoroutine,
    BlockData,
    RPCEndpoint,
    RPCResponse,
)

if TYPE_CHECKING:
    from web3 import (  # noqa: F401
        AsyncWeb3,
        Web3,
    )

SKIP_STALECHECK_FOR_METHODS = ("eth_getBlockByNumber",)


def _is_fresh(block: BlockData, allowable_delay: int) -> bool:
    if block and (time.time() - block["timestamp"] <= allowable_delay):
        return True
    return False


class StaleCheckMiddleware(Web3Middleware):
    def __init__(
        self,
        allowable_delay: int,
        skip_stalecheck_for_methods: Collection[str] = SKIP_STALECHECK_FOR_METHODS,
    ) -> None:
        if allowable_delay <= 0:
            raise ValueError(
                "You must set a positive allowable_delay in seconds for this middleware"
            )

        self.allowable_delay = allowable_delay
        self.skip_stalecheck_for_methods = skip_stalecheck_for_methods
        self.cache: Dict[str, Optional[BlockData]] = {"latest": None}

    def request_processor(self, w3: "Web3", method: "RPCEndpoint", params: Any) -> Any:
        if method not in self.skip_stalecheck_for_methods:
            if not _is_fresh(self.cache["latest"], self.allowable_delay):
                latest = w3.eth.get_block("latest")
                if _is_fresh(latest, self.allowable_delay):
                    self.cache["latest"] = latest
                else:
                    raise StaleBlockchain(latest, self.allowable_delay)

        return params

    # -- async -- #

    async def async_request_processor(
        self, w3: "AsyncWeb3", method: "RPCEndpoint", params: Any
    ) -> Any:
        if method not in self.skip_stalecheck_for_methods:
            if not _is_fresh(self.cache["latest"], self.allowable_delay):
                latest = await w3.eth.get_block("latest")
                if _is_fresh(latest, self.allowable_delay):
                    self.cache["latest"] = latest
                else:
                    raise StaleBlockchain(latest, self.allowable_delay)

        return params


# -- async -- #


async def async_make_stalecheck_middleware(
    allowable_delay: int,
    skip_stalecheck_for_methods: Collection[str] = SKIP_STALECHECK_FOR_METHODS,
) -> AsyncMiddleware:
    """
    Use to require that a function will run only of the blockchain is recently updated.

    This middleware takes an argument, so unlike other middleware, you must make the
    middleware with a method call.

    For example: `async_make_stalecheck_middleware(60*5)`

    If the latest block in the chain is older than 5 minutes in this example, then the
    middleware will raise a StaleBlockchain exception.
    """
    if allowable_delay <= 0:
        raise ValueError(
            "You must set a positive allowable_delay in seconds for this middleware"
        )

    async def stalecheck_middleware(
        make_request: Callable[[RPCEndpoint, Any], Any], w3: "AsyncWeb3"
    ) -> AsyncMiddlewareCoroutine:
        cache: Dict[str, Optional[BlockData]] = {"latest": None}

        async def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
            if method not in skip_stalecheck_for_methods:
                if not _is_fresh(cache["latest"], allowable_delay):
                    latest = await w3.eth.get_block("latest")
                    if _is_fresh(latest, allowable_delay):
                        cache["latest"] = latest
                    else:
                        raise StaleBlockchain(latest, allowable_delay)

            return await make_request(method, params)

        return middleware

    return stalecheck_middleware
