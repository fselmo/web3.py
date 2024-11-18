from typing import (
    TYPE_CHECKING,
    List,
    Sequence,
    Union,
    cast,
    overload,
)

from eth_typing import (
    HexStr,
)
from typing_extensions import (
    TypeVar,
)

from web3.exceptions import (
    Web3TypeError,
    Web3ValueError,
)
from web3.utils import (
    EthSubscription,
)

if TYPE_CHECKING:
    from web3 import AsyncWeb3  # noqa: F401
    from web3.providers.persistent import PersistentConnectionProvider  # noqa: F401


T = TypeVar("T", bound="EthSubscription")


class SubscriptionManager:
    _provider: "PersistentConnectionProvider"

    def __init__(self, w3: "AsyncWeb3") -> None:
        self._w3 = w3
        self._provider = cast("PersistentConnectionProvider", w3.provider)
        self.subscriptions: List[EthSubscription] = []

    @overload
    async def subscribe(self, subscription: T) -> HexStr:
        ...

    @overload
    async def subscribe(self, subscription: Sequence[T]) -> List[HexStr]:
        ...

    async def subscribe(
        self, subscription: Union[T, Sequence[T]]
    ) -> Union[HexStr, List[HexStr]]:
        if isinstance(subscription, EthSubscription):
            subscription._manager = self
            sxn_id = await self._w3.eth._subscribe(*subscription.subscription_params)
            subscription._id = sxn_id
            self.subscriptions.append(subscription)
            self._provider.logger.info(
                f"Successfully subscribed to subscription:\n    "
                f"label: {subscription.label}\n    id: {sxn_id}"
            )
            return sxn_id
        elif isinstance(subscription, Sequence):
            if len(subscription) == 0:
                raise Web3ValueError("No subscriptions provided.")

            sxn_ids = []
            for sxn in subscription:
                await self.subscribe(sxn)
                sxn_ids.append(sxn._id)

            return sxn_ids
        else:
            raise Web3TypeError(
                "Expected a Subscription or a sequence of Subscriptions."
            )

    async def unsubscribe(self, sxn: EthSubscription) -> bool:
        if sxn not in self.subscriptions:
            raise Web3ValueError(
                f"Subscription not found or is not being managed by the subscription "
                f"manager.\n    label: {sxn.label}\n    id: {sxn._id}"
            )

        if await self._w3.eth._unsubscribe(sxn.id):
            self.subscriptions.remove(sxn)
            return True
        return False

    async def unsubscribe_all(self) -> None:
        for sx in self.subscriptions:
            await self.unsubscribe(sx)

        self._provider.logger.info("Successfully unsubscribed from all subscriptions.")

    async def _handle_subscriptions(self, run_forever: bool = False) -> None:
        self._provider.logger.info("Subscription manager processing started.")
        while True:
            if not run_forever and len(self.subscriptions) == 0:
                break
            await self._w3.manager._get_next_message()

        self._provider.logger.info(
            "Subscription manager processing ended for "
            f"{self._provider.get_endpoint_uri_or_ipc_path()}"
        )

    async def handle_subscriptions(self, run_forever: bool = False) -> None:
        await self._handle_subscriptions(run_forever=run_forever)
