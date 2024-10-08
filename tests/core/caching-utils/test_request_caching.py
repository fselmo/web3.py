import itertools
import pytest
import threading
import uuid

import pytest_asyncio

from web3 import (
    AsyncHTTPProvider,
    AsyncIPCProvider,
    AsyncWeb3,
    HTTPProvider,
    IPCProvider,
    LegacyWebSocketProvider,
    Web3,
    WebSocketProvider,
)
from web3._utils.caching import (
    CACHEABLE_REQUESTS,
    generate_cache_key,
)
from web3._utils.caching.caching_utils import (
    ASYNC_INTERNAL_VALIDATION_MAP,
    BLOCKHASH_IN_PARAMS,
    BLOCKNUM_IN_PARAMS,
    BLOCKNUM_IN_RESULT,
    INTERNAL_VALIDATION_MAP,
)
from web3.exceptions import (
    Web3RPCError,
)
from web3.providers import (
    AsyncBaseProvider,
    BaseProvider,
    JSONBaseProvider,
)
from web3.providers.async_base import (
    AsyncJSONBaseProvider,
)
from web3.types import (
    RPCEndpoint,
)
from web3.utils import (
    RequestCacheValidationThreshold,
    SimpleCache,
)


def simple_cache_return_value_a():
    _cache = SimpleCache()
    _cache.cache(
        generate_cache_key(f"{threading.get_ident()}:{('fake_endpoint', [1])}"),
        {"jsonrpc": "2.0", "id": 0, "result": "value-a"},
    )
    return _cache


@pytest.fixture
def w3(request_mocker):
    _w3 = Web3(provider=BaseProvider(cache_allowed_requests=True))
    _w3.provider.cacheable_requests += (RPCEndpoint("fake_endpoint"),)
    with request_mocker(
        _w3,
        mock_results={
            "fake_endpoint": lambda *_: uuid.uuid4(),
            "not_on_allowlist": lambda *_: uuid.uuid4(),
        },
    ):
        yield _w3

    # clear request cache after each test
    _w3.provider._request_cache.clear()


def test_request_caching_pulls_from_cache(w3):
    w3.provider._request_cache = simple_cache_return_value_a()
    assert w3.manager.request_blocking("fake_endpoint", [1]) == "value-a"


def test_request_caching_populates_cache(w3):
    result = w3.manager.request_blocking("fake_endpoint", [])
    assert w3.manager.request_blocking("fake_endpoint", []) == result
    assert w3.manager.request_blocking("fake_endpoint", [1]) != result
    assert len(w3.provider._request_cache.items()) == 2


def test_request_caching_does_not_cache_none_responses(request_mocker):
    w3 = Web3(BaseProvider(cache_allowed_requests=True))
    w3.provider.cacheable_requests += (RPCEndpoint("fake_endpoint"),)

    counter = itertools.count()

    def result_cb(_method, _params):
        next(counter)
        return None

    with request_mocker(w3, mock_results={"fake_endpoint": result_cb}):
        w3.manager.request_blocking("fake_endpoint", [])
        w3.manager.request_blocking("fake_endpoint", [])

    assert next(counter) == 2


def test_request_caching_does_not_cache_error_responses(request_mocker):
    w3 = Web3(BaseProvider(cache_allowed_requests=True))
    w3.provider.cacheable_requests += (RPCEndpoint("fake_endpoint"),)

    with request_mocker(
        w3, mock_errors={"fake_endpoint": lambda *_: {"message": f"msg-{uuid.uuid4()}"}}
    ):
        with pytest.raises(Web3RPCError) as err_a:
            w3.manager.request_blocking("fake_endpoint", [])
        with pytest.raises(Web3RPCError) as err_b:
            w3.manager.request_blocking("fake_endpoint", [])

        assert str(err_a) != str(err_b)
        assert err_a.value.args != err_b.value.args


def test_request_caching_does_not_cache_endpoints_not_in_allowlist(w3):
    result_a = w3.manager.request_blocking("not_on_allowlist", [])
    result_b = w3.manager.request_blocking("not_on_allowlist", [])
    assert result_a != result_b


def test_caching_requests_does_not_share_state_between_providers(request_mocker):
    w3_a, w3_b, w3_c, w3_a_shared_cache = (
        Web3(provider=BaseProvider(cache_allowed_requests=True)),
        Web3(provider=BaseProvider(cache_allowed_requests=True)),
        Web3(provider=BaseProvider(cache_allowed_requests=True)),
        Web3(provider=BaseProvider(cache_allowed_requests=True)),
    )

    # strap w3_a_shared_cache with w3_a's cache
    w3_a_shared_cache.provider._request_cache = w3_a.provider._request_cache

    mock_results_a = {RPCEndpoint("eth_chainId"): 11111}
    mock_results_a_shared_cache = {RPCEndpoint("eth_chainId"): 00000}
    mock_results_b = {RPCEndpoint("eth_chainId"): 22222}
    mock_results_c = {RPCEndpoint("eth_chainId"): 33333}

    with request_mocker(w3_a, mock_results=mock_results_a):
        with request_mocker(w3_b, mock_results=mock_results_b):
            with request_mocker(w3_c, mock_results=mock_results_c):
                result_a = w3_a.manager.request_blocking("eth_chainId", [])
                result_b = w3_b.manager.request_blocking("eth_chainId", [])
                result_c = w3_c.manager.request_blocking("eth_chainId", [])

        with request_mocker(
            w3_a_shared_cache, mock_results=mock_results_a_shared_cache
        ):
            # test a shared cache returns 11111, not 00000
            result_a_shared_cache = w3_a_shared_cache.manager.request_blocking(
                "eth_chainId", []
            )

    assert result_a == 11111
    assert result_b == 22222
    assert result_c == 33333
    assert result_a_shared_cache == 11111


@pytest.mark.parametrize(
    "provider",
    [
        BaseProvider,
        JSONBaseProvider,
        HTTPProvider,
        IPCProvider,
        AsyncBaseProvider,
        AsyncJSONBaseProvider,
        AsyncHTTPProvider,
        AsyncIPCProvider,
        WebSocketProvider,
        LegacyWebSocketProvider,  # deprecated
    ],
)
def test_all_providers_do_not_cache_by_default_and_can_set_caching_properties(provider):
    _provider_default_init = provider()
    assert _provider_default_init.cache_allowed_requests is False
    assert _provider_default_init.cacheable_requests == CACHEABLE_REQUESTS

    # can set properties
    _provider_default_init.cache_allowed_requests = True
    _provider_default_init.cacheable_requests = {RPCEndpoint("fake_endpoint")}
    assert _provider_default_init.cache_allowed_requests is True
    assert _provider_default_init.cacheable_requests == {RPCEndpoint("fake_endpoint")}

    # can set properties on init
    _provider_set_on_init = provider(
        cache_allowed_requests=True,
        cacheable_requests={RPCEndpoint("fake_endpoint")},
    )
    assert _provider_set_on_init.cache_allowed_requests is True
    assert _provider_set_on_init.cacheable_requests == {RPCEndpoint("fake_endpoint")}


@pytest.mark.parametrize(
    "threshold",
    (RequestCacheValidationThreshold.FINALIZED, RequestCacheValidationThreshold.SAFE),
)
@pytest.mark.parametrize("endpoint", BLOCKNUM_IN_PARAMS | BLOCKNUM_IN_RESULT)
@pytest.mark.parametrize(
    "blocknum,should_cache",
    (
        ("0x0", True),
        ("0x1", True),
        ("0x2", True),
        ("0x3", False),
        ("0x4", False),
        ("0x5", False),
    ),
)
def test_blocknum_validation_against_validation_threshold_when_caching(
    threshold, endpoint, blocknum, should_cache, request_mocker
):
    w3 = Web3(
        HTTPProvider(
            cache_allowed_requests=True, request_cache_validation_threshold=threshold
        )
    )
    with request_mocker(
        w3,
        mock_results={
            endpoint: (
                # mock the result to requests that return blocks
                {"number": blocknum}
                if "getBlock" in endpoint
                # mock the result to requests that return transactions
                else {"blockNumber": blocknum}
            ),
            "eth_getBlockByNumber": lambda _method, params: (
                # mock the threshold block to be blocknum "0x2", return
                # blocknum otherwise
                {"number": "0x2"}
                if params[0] == threshold.value
                else {"number": params[0]}
            ),
        },
    ):
        assert len(w3.provider._request_cache.items()) == 0
        w3.manager.request_blocking(endpoint, [blocknum, False])
        cached_items = len(w3.provider._request_cache.items())
        assert cached_items == 1 if should_cache else cached_items == 0


@pytest.mark.parametrize(
    "threshold",
    (RequestCacheValidationThreshold.FINALIZED, RequestCacheValidationThreshold.SAFE),
)
@pytest.mark.parametrize("endpoint", BLOCKNUM_IN_PARAMS)
@pytest.mark.parametrize(
    "block_id,blocknum,should_cache",
    (
        ("earliest", "0x0", True),
        ("earliest", "0x2", True),
        ("finalized", "0x2", False),
        ("safe", "0x2", False),
        ("latest", "0x2", False),
        ("pending", None, False),
    ),
)
def test_block_id_param_caching(
    threshold, endpoint, block_id, blocknum, should_cache, request_mocker
):
    w3 = Web3(
        HTTPProvider(
            cache_allowed_requests=True, request_cache_validation_threshold=threshold
        )
    )
    with request_mocker(
        w3,
        mock_results={
            endpoint: "0x0",
            "eth_getBlockByNumber": lambda _method, params: (
                # mock the threshold block to be blocknum "0x2" for all test cases
                {"number": "0x2"}
                if params[0] == threshold.value
                else {"number": blocknum}
            ),
        },
    ):
        assert len(w3.provider._request_cache.items()) == 0
        w3.manager.request_blocking(RPCEndpoint(endpoint), [block_id, False])
        cached_items = len(w3.provider._request_cache.items())
        assert cached_items == 1 if should_cache else cached_items == 0


@pytest.mark.parametrize(
    "threshold",
    (RequestCacheValidationThreshold.FINALIZED, RequestCacheValidationThreshold.SAFE),
)
@pytest.mark.parametrize("endpoint", BLOCKHASH_IN_PARAMS)
@pytest.mark.parametrize(
    "blocknum,should_cache",
    (
        ("0x0", True),
        ("0x1", True),
        ("0x2", True),
        ("0x3", False),
        ("0x4", False),
        ("0x5", False),
    ),
)
def test_blockhash_validation_against_validation_threshold_when_caching(
    threshold, endpoint, blocknum, should_cache, request_mocker
):
    w3 = Web3(
        HTTPProvider(
            cache_allowed_requests=True, request_cache_validation_threshold=threshold
        )
    )
    with request_mocker(
        w3,
        mock_results={
            "eth_getBlockByNumber": lambda _method, params: (
                # mock the threshold block to be blocknum "0x2"
                {"number": "0x2"}
                if params[0] == threshold.value
                else {"number": params[0]}
            ),
            "eth_getBlockByHash": {"number": blocknum},
            endpoint: "0x0",
        },
    ):
        assert len(w3.provider._request_cache.items()) == 0
        w3.manager.request_blocking(endpoint, [b"\x00" * 32, False])
        cached_items = len(w3.provider._request_cache.items())
        assert cached_items == 2 if should_cache else cached_items == 0


def test_request_caching_validation_threshold_is_finalized_by_default():
    w3 = Web3(HTTPProvider(cache_allowed_requests=True))
    assert (
        w3.provider.request_cache_validation_threshold
        == RequestCacheValidationThreshold.FINALIZED
    )


@pytest.mark.parametrize(
    "endpoint", BLOCKNUM_IN_PARAMS | BLOCKNUM_IN_RESULT | BLOCKHASH_IN_PARAMS
)
@pytest.mark.parametrize("blocknum", ("0x0", "0x1", "0x2", "0x3", "0x4", "0x5"))
def test_request_caching_with_validation_threshold_set_to_none(
    endpoint, blocknum, request_mocker
):
    w3 = Web3(
        HTTPProvider(
            cache_allowed_requests=True,
            request_cache_validation_threshold=None,
        )
    )
    with request_mocker(w3, mock_results={endpoint: {"number": blocknum}}):
        assert len(w3.provider._request_cache.items()) == 0
        w3.manager.request_blocking(endpoint, [blocknum, False])
        assert len(w3.provider._request_cache.items()) == 1


# -- async -- #


def test_async_cacheable_requests_are_the_same_as_sync():
    assert (
        set(CACHEABLE_REQUESTS)
        == set(INTERNAL_VALIDATION_MAP.keys())
        == set(ASYNC_INTERNAL_VALIDATION_MAP.keys())
    ), "make sure the async and sync cacheable requests are the same"


@pytest_asyncio.fixture
async def async_w3(request_mocker):
    _async_w3 = AsyncWeb3(AsyncBaseProvider(cache_allowed_requests=True))
    _async_w3.provider.cacheable_requests += (RPCEndpoint("fake_endpoint"),)
    async with request_mocker(
        _async_w3,
        mock_results={
            "fake_endpoint": lambda *_: uuid.uuid4(),
            "not_on_allowlist": lambda *_: uuid.uuid4(),
        },
    ):
        yield _async_w3

    # clear request cache after each test
    _async_w3.provider._request_cache.clear()


@pytest.mark.asyncio
async def test_async_request_caching_pulls_from_cache(async_w3):
    async_w3.provider._request_cache = simple_cache_return_value_a()
    _result = await async_w3.manager.coro_request("fake_endpoint", [1])
    assert _result == "value-a"


@pytest.mark.asyncio
async def test_async_request_caching_populates_cache(async_w3):
    result = await async_w3.manager.coro_request("fake_endpoint", [])

    _empty_params = await async_w3.manager.coro_request("fake_endpoint", [])
    _non_empty_params = await async_w3.manager.coro_request("fake_endpoint", [1])

    assert _empty_params == result
    assert _non_empty_params != result


@pytest.mark.asyncio
async def test_async_request_caching_does_not_cache_none_responses(request_mocker):
    async_w3 = AsyncWeb3(AsyncBaseProvider(cache_allowed_requests=True))
    async_w3.provider.cacheable_requests += (RPCEndpoint("fake_endpoint"),)

    counter = itertools.count()

    def result_cb(_method, _params):
        next(counter)
        return None

    async with request_mocker(async_w3, mock_results={"fake_endpoint": result_cb}):
        await async_w3.manager.coro_request("fake_endpoint", [])
        await async_w3.manager.coro_request("fake_endpoint", [])

    assert next(counter) == 2


@pytest.mark.asyncio
async def test_async_request_caching_does_not_cache_error_responses(request_mocker):
    async_w3 = AsyncWeb3(AsyncBaseProvider(cache_allowed_requests=True))
    async_w3.provider.cacheable_requests += (RPCEndpoint("fake_endpoint"),)

    async with request_mocker(
        async_w3,
        mock_errors={"fake_endpoint": lambda *_: {"message": f"msg-{uuid.uuid4()}"}},
    ):
        with pytest.raises(Web3RPCError) as err_a:
            await async_w3.manager.coro_request("fake_endpoint", [])
        with pytest.raises(Web3RPCError) as err_b:
            await async_w3.manager.coro_request("fake_endpoint", [])

    assert str(err_a) != str(err_b)


@pytest.mark.asyncio
async def test_async_request_caching_does_not_cache_non_allowlist_endpoints(
    async_w3,
):
    result_a = await async_w3.manager.coro_request("not_on_allowlist", [])
    result_b = await async_w3.manager.coro_request("not_on_allowlist", [])
    assert result_a != result_b


@pytest.mark.asyncio
async def test_async_request_caching_does_not_share_state_between_providers(
    request_mocker,
):
    async_w3_a, async_w3_b, async_w3_c, async_w3_a_shared_cache = (
        AsyncWeb3(AsyncBaseProvider(cache_allowed_requests=True)),
        AsyncWeb3(AsyncBaseProvider(cache_allowed_requests=True)),
        AsyncWeb3(AsyncBaseProvider(cache_allowed_requests=True)),
        AsyncWeb3(AsyncBaseProvider(cache_allowed_requests=True)),
    )

    # strap async_w3_a_shared_cache with async_w3_a's cache
    async_w3_a_shared_cache.provider._request_cache = async_w3_a.provider._request_cache

    mock_results_a = {RPCEndpoint("eth_chainId"): 11111}
    mock_results_a_shared_cache = {RPCEndpoint("eth_chainId"): 00000}
    mock_results_b = {RPCEndpoint("eth_chainId"): 22222}
    mock_results_c = {RPCEndpoint("eth_chainId"): 33333}

    async with request_mocker(async_w3_a, mock_results=mock_results_a):
        async with request_mocker(async_w3_b, mock_results=mock_results_b):
            async with request_mocker(async_w3_c, mock_results=mock_results_c):
                result_a = await async_w3_a.manager.coro_request("eth_chainId", [])
                result_b = await async_w3_b.manager.coro_request("eth_chainId", [])
                result_c = await async_w3_c.manager.coro_request("eth_chainId", [])

        async with request_mocker(
            async_w3_a_shared_cache, mock_results=mock_results_a_shared_cache
        ):
            # test a shared cache returns 11111, not 00000
            result_a_shared_cache = await async_w3_a_shared_cache.manager.coro_request(
                "eth_chainId", []
            )

    assert result_a == 11111
    assert result_b == 22222
    assert result_c == 33333
    assert result_a_shared_cache == 11111


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "threshold",
    (RequestCacheValidationThreshold.FINALIZED, RequestCacheValidationThreshold.SAFE),
)
@pytest.mark.parametrize("endpoint", BLOCKNUM_IN_PARAMS | BLOCKNUM_IN_RESULT)
@pytest.mark.parametrize(
    "blocknum,should_cache",
    (
        ("0x0", True),
        ("0x1", True),
        ("0x2", True),
        ("0x3", False),
        ("0x4", False),
        ("0x5", False),
    ),
)
async def test_async_blocknum_validation_against_validation_threshold(
    threshold, endpoint, blocknum, should_cache, request_mocker
):
    async_w3 = AsyncWeb3(
        AsyncHTTPProvider(
            cache_allowed_requests=True, request_cache_validation_threshold=threshold
        )
    )
    async with request_mocker(
        async_w3,
        mock_results={
            endpoint: (
                # mock the result to requests that return blocks
                {"number": blocknum}
                if "getBlock" in endpoint
                # mock the result to requests that return transactions
                else {"blockNumber": blocknum}
            ),
            "eth_getBlockByNumber": lambda _method, params: (
                # mock the threshold block to be blocknum "0x2", return
                # blocknum otherwise
                {"number": "0x2"}
                if params[0] == threshold.value
                else {"number": params[0]}
            ),
        },
    ):
        assert len(async_w3.provider._request_cache.items()) == 0
        await async_w3.manager.coro_request(endpoint, [blocknum, False])
        cached_items = len(async_w3.provider._request_cache.items())
        assert cached_items == 1 if should_cache else cached_items == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "threshold",
    (RequestCacheValidationThreshold.FINALIZED, RequestCacheValidationThreshold.SAFE),
)
@pytest.mark.parametrize("endpoint", BLOCKNUM_IN_PARAMS)
@pytest.mark.parametrize(
    "block_id,blocknum,should_cache",
    (
        ("earliest", "0x0", True),
        ("earliest", "0x2", True),
        ("finalized", "0x2", False),
        ("safe", "0x2", False),
        ("latest", "0x2", False),
        ("pending", None, False),
    ),
)
async def test_async_block_id_param_caching(
    threshold, endpoint, block_id, blocknum, should_cache, request_mocker
):
    async_w3 = AsyncWeb3(
        AsyncHTTPProvider(
            cache_allowed_requests=True, request_cache_validation_threshold=threshold
        )
    )
    async with request_mocker(
        async_w3,
        mock_results={
            endpoint: "0x0",
            "eth_getBlockByNumber": lambda _method, params: (
                # mock the threshold block to be blocknum "0x2" for all test cases
                {"number": "0x2"}
                if params[0] == threshold.value
                else {"number": blocknum}
            ),
        },
    ):
        assert len(async_w3.provider._request_cache.items()) == 0
        await async_w3.manager.coro_request(RPCEndpoint(endpoint), [block_id, False])
        cached_items = len(async_w3.provider._request_cache.items())
        assert cached_items == 1 if should_cache else cached_items == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "threshold",
    (RequestCacheValidationThreshold.FINALIZED, RequestCacheValidationThreshold.SAFE),
)
@pytest.mark.parametrize("endpoint", BLOCKHASH_IN_PARAMS)
@pytest.mark.parametrize(
    "blocknum,should_cache",
    (
        ("0x0", True),
        ("0x1", True),
        ("0x2", True),
        ("0x3", False),
        ("0x4", False),
        ("0x5", False),
    ),
)
async def test_async_blockhash_validation_against_validation_threshold(
    threshold, endpoint, blocknum, should_cache, request_mocker
):
    async_w3 = AsyncWeb3(
        AsyncHTTPProvider(
            cache_allowed_requests=True, request_cache_validation_threshold=threshold
        )
    )
    async with request_mocker(
        async_w3,
        mock_results={
            "eth_getBlockByNumber": lambda _method, params: (
                # mock the threshold block to be blocknum "0x2"
                {"number": "0x2"}
                if params[0] == threshold.value
                else {"number": params[0]}
            ),
            "eth_getBlockByHash": {"number": blocknum},
            endpoint: "0x0",
        },
    ):
        assert len(async_w3.provider._request_cache.items()) == 0
        await async_w3.manager.coro_request(endpoint, [b"\x00" * 32, False])
        cached_items = len(async_w3.provider._request_cache.items())
        assert cached_items == 2 if should_cache else cached_items == 0


@pytest.mark.asyncio
async def test_async_request_caching_validation_threshold_is_finalized_by_default():
    async_w3 = AsyncWeb3(AsyncHTTPProvider(cache_allowed_requests=True))
    assert (
        async_w3.provider.request_cache_validation_threshold
        == RequestCacheValidationThreshold.FINALIZED
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint", BLOCKNUM_IN_PARAMS | BLOCKNUM_IN_RESULT | BLOCKHASH_IN_PARAMS
)
@pytest.mark.parametrize("blocknum", ("0x0", "0x1", "0x2", "0x3", "0x4", "0x5"))
async def test_async_request_caching_with_validation_threshold_set_to_none(
    endpoint, blocknum, request_mocker
):
    async_w3 = AsyncWeb3(
        AsyncHTTPProvider(
            cache_allowed_requests=True,
            request_cache_validation_threshold=None,
        )
    )
    async with request_mocker(async_w3, mock_results={endpoint: {"number": blocknum}}):
        assert len(async_w3.provider._request_cache.items()) == 0
        await async_w3.manager.coro_request(endpoint, [blocknum, False])
        assert len(async_w3.provider._request_cache.items()) == 1
