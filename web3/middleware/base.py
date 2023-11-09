from typing import (
    TYPE_CHECKING,
    Any,
)

if TYPE_CHECKING:
    from web3 import (
        AsyncWeb3,
        Web3,
    )
    from web3.types import (
        RPCEndpoint,
        RPCResponse,
    )


class Web3Middleware:
    @classmethod
    def request_processor(cls, w3: "Web3", method: "RPCEndpoint", params: Any) -> Any:
        return params

    @classmethod
    def response_processor(
        cls, w3: "Web3", method: "RPCEndpoint", response: "RPCResponse"
    ) -> "RPCResponse":
        return response

    # -- async -- #

    @classmethod
    async def async_request_processor(
        cls,
        async_w3: "AsyncWeb3",
        method: "RPCEndpoint",
        params: Any,
    ) -> Any:
        return params

    @classmethod
    async def async_response_processor(
        cls,
        async_w3: "AsyncWeb3",
        method: "RPCEndpoint",
        response: "RPCResponse",
    ) -> "RPCResponse":
        return response
