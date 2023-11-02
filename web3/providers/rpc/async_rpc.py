import asyncio
import logging
from typing import (
    Any,
    Collection,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

from aiohttp import (
    ClientSession,
)
from eth_typing import (
    URI,
)
from eth_utils import (
    to_dict,
)

from web3._utils.http import (
    construct_user_agent,
)
from web3._utils.request import (
    async_cache_and_return_session as _async_cache_and_return_session,
    async_make_post_request,
    get_default_http_endpoint,
)
from web3.types import (
    AsyncMiddleware,
    RPCEndpoint,
    RPCResponse,
)
from .utils import ExceptionRetryConfiguration

from ...datastructures import (
    NamedElementOnion,
)
from ..async_base import (
    AsyncJSONBaseProvider,
)


def check_if_retry_on_failure(method: RPCEndpoint, allowlist: Collection[str]) -> bool:
    root = method.split("_")[0]
    if root in allowlist:
        return True
    elif method in allowlist:
        return True
    else:
        return False


class AsyncHTTPProvider(AsyncJSONBaseProvider):
    logger = logging.getLogger("web3.providers.AsyncHTTPProvider")
    endpoint_uri = None
    _request_kwargs = None
    # type ignored b/c conflict with _middlewares attr on AsyncBaseProvider
    _middlewares: Tuple[AsyncMiddleware, ...] = NamedElementOnion([])  # type: ignore

    def __init__(
        self,
        endpoint_uri: Optional[Union[URI, str]] = None,
        request_kwargs: Optional[Any] = None,
        exception_retry_configuration: Optional[ExceptionRetryConfiguration] = None,
    ) -> None:
        if endpoint_uri is None:
            self.endpoint_uri = get_default_http_endpoint()
        else:
            self.endpoint_uri = URI(endpoint_uri)

        self._request_kwargs = request_kwargs or {}

        self.exception_retry_configuration = (
            exception_retry_configuration
            # use default values if not provided
            or ExceptionRetryConfiguration()
        )

        super().__init__()

    async def cache_async_session(self, session: ClientSession) -> ClientSession:
        return await _async_cache_and_return_session(self.endpoint_uri, session)

    def __str__(self) -> str:
        return f"RPC connection {self.endpoint_uri}"

    @to_dict
    def get_request_kwargs(self) -> Iterable[Tuple[str, Any]]:
        if "headers" not in self._request_kwargs:
            yield "headers", self.get_request_headers()
        for key, value in self._request_kwargs.items():
            yield key, value

    def get_request_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "User-Agent": construct_user_agent(str(type(self))),
        }

    async def _make_request(self, method: RPCEndpoint, request_data: bytes) -> bytes:
        """
        If exception_retry_configuration is set, retry on failure; otherwise, make
        the request without retrying.
        """
        if (
            self.exception_retry_configuration is not None
            and check_if_retry_on_failure(
                method, self.exception_retry_configuration.method_allowlist
            )
        ):
            for i in range(self.exception_retry_configuration.retries):
                try:
                    return await async_make_post_request(
                        self.endpoint_uri, request_data, **self.get_request_kwargs()
                    )
                except tuple(self.exception_retry_configuration.errors):
                    if i < self.exception_retry_configuration.retries - 1:
                        await asyncio.sleep(
                            self.exception_retry_configuration.backoff_factor
                        )
                        continue
                    else:
                        raise
        else:
            return await async_make_post_request(
                self.endpoint_uri, request_data, **self.get_request_kwargs()
            )

    async def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        self.logger.debug(
            f"Making request HTTP. URI: {self.endpoint_uri}, Method: {method}"
        )
        request_data = self.encode_rpc_request(method, params)
        raw_response = await self._make_request(method, request_data)
        response = self.decode_rpc_response(raw_response)
        self.logger.debug(
            f"Getting response HTTP. URI: {self.endpoint_uri}, "
            f"Method: {method}, Response: {response}"
        )
        return response

    async def make_batch_request(
        self, requests_info: Iterable[Tuple[RPCEndpoint, Any]]
    ) -> List[RPCResponse]:
        self.logger.debug(f"Making batch request HTTP. URI: {self.endpoint_uri}")
        requests = [request_info[0] for request_info in requests_info]
        request_data: bytes = self.encode_batch_rpc_request(requests)
        raw_response: bytes = await async_make_post_request(
            self.endpoint_uri, request_data, **self.get_request_kwargs()
        )
        response: List[RPCResponse] = self.decode_batch_rpc_response(raw_response)
        self.logger.debug(f"Getting batch response HTTP. URI: {self.endpoint_uri}")
        return response