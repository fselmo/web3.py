from types import (
    TracebackType,
)
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    List,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)

from web3._utils.compat import (
    Self,
)
from web3.method import (
    Method,
)
from web3.types import (
    TFunc,
    TReturn,
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

BatchRequestInformation = Tuple[Tuple["RPCEndpoint", Any], Sequence[Any]]


class BatchRequestContextManager(Generic[TFunc]):
    def __init__(self, web3: Union["AsyncWeb3", "Web3"]) -> None:
        self.web3 = web3
        self._requests_info: List[BatchRequestInformation] = []

    def add(self, batch_payload: Union[TReturn, Sequence[TReturn]]) -> None:
        # When batching, we don't make a request. Instead, we will get the request
        # information and store it in the _requests_info list.
        if isinstance(batch_payload, Sequence):
            for request_information in batch_payload:
                self._requests_info.append(
                    cast(BatchRequestInformation, request_information)
                )
        else:
            self._requests_info.append(cast(BatchRequestInformation, batch_payload))

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
        return self.web3.manager.make_batch_request(self._requests_info)

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
        return await self.web3.manager.async_make_batch_request(self._requests_info)