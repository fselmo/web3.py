from types import (
    TracebackType,
)
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Self,
    Type,
    Union,
)

if TYPE_CHECKING:
    from web3 import (  # noqa: F401
        AsyncWeb3,
        Web3,
    )
    from web3.types import (  # noqa: F401
        RPCEndpoint,
        RPCResponse,
    )


class BatchRequestContextManager:
    def __init__(self, web3: Union["AsyncWeb3", "Web3"]) -> None:
        self.web3 = web3
        # TODO: use a more specific type than Any
        self._requests: List[Any] = []

    def add(self, request: Any) -> None:
        self._requests.append(request)

    def __enter__(self) -> Self:
        self.web3._is_batching = True
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self.web3._is_batching = False

    def execute(self) -> List["RPCResponse"]:
        return self.web3.manager.make_batch_request(self._requests)

    # -- async -- #

    async def __aenter__(self) -> Self:
        self.web3._is_batching = True
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self.web3._is_batching = False

    async def async_execute(self) -> List["RPCResponse"]:
        return await self.web3.manager.async_make_batch_request(self._requests)
