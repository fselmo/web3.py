import logging
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Sequence,
    Union,
    cast,
    overload,
)

from eth_typing import (
    HexStr,
)

from web3.exceptions import (
    Web3TypeError,
    Web3ValueError,
)
from web3.utils.subscriptions import (
    EthSubscription,
)

if TYPE_CHECKING:
    from web3 import AsyncWeb3  # noqa: F401
    from web3.providers.persistent import PersistentConnectionProvider  # noqa: F401


class SubscriptionManager:
    logger: logging.Logger = logging.getLogger(
        "web3.providers.persistent.subscription_manager"
    )
    total_handler_calls: int = 0

    def __init__(self, w3: "AsyncWeb3") -> None:
        self._w3 = w3
        self._provider = cast("PersistentConnectionProvider", w3.provider)
        self.subscriptions: List[EthSubscription[Any]] = []

    @overload
    async def subscribe(self, subscriptions: EthSubscription[Any]) -> HexStr:
        ...

    @overload
    async def subscribe(
        self, subscriptions: Sequence[EthSubscription[Any]]
    ) -> List[HexStr]:
        ...

    async def subscribe(
        self, subscriptions: Union[EthSubscription[Any], Sequence[EthSubscription[Any]]]
    ) -> Union[HexStr, List[HexStr]]:
        if isinstance(subscriptions, EthSubscription):
            subscriptions._manager = self
            sx_id = await self._w3.eth._subscribe(*subscriptions.subscription_params)
            subscriptions._id = sx_id
            self.subscriptions.append(subscriptions)
            self.logger.info(
                "Successfully subscribed to subscription:\n    "
                f"label: {subscriptions.label}\n    id: {sx_id}"
            )
            return sx_id
        elif isinstance(subscriptions, Sequence):
            if len(subscriptions) == 0:
                raise Web3ValueError("No subscriptions provided.")

            sx_ids = []
            for sx in subscriptions:
                await self.subscribe(sx)
                sx_ids.append(sx._id)

            return sx_ids
        else:
            raise Web3TypeError(
                "Expected a Subscription or a sequence of Subscriptions."
            )

    async def unsubscribe(self, subscription: EthSubscription[Any]) -> bool:
        """
        Used to unsubscribe from a subscription that is being managed by the
        subscription manager.

        :param subscription: The subscription to unsubscribe from.
        :return: True if unsubscribing was successful, False otherwise.
        """
        if subscription not in self.subscriptions:
            raise Web3ValueError(
                f"Subscription not found or is not being managed by the subscription "
                f"manager.\n    label: {subscription.label}\n    id: {subscription._id}"
            )

        if await self._w3.eth._unsubscribe(subscription.id):
            self.subscriptions.remove(subscription)
            return True
        return False

    async def unsubscribe_all(self) -> None:
        """
        Used to unsubscribe from all subscriptions that are being managed by the
        subscription manager.

        :return: None
        """
        for sx in self.subscriptions:
            await self.unsubscribe(sx)

        self.logger.info("Successfully unsubscribed from all subscriptions.")

    async def _handle_subscriptions(self, run_forever: bool = False) -> None:
        self.logger.info("Subscription manager processing started.")
        while True:
            if not run_forever and len(self.subscriptions) == 0:
                break
            await self._w3.manager._get_next_message()

        self.logger.info("Subscription manager processing ended.")

    async def handle_subscriptions(self, run_forever: bool = False) -> None:
        """
        Used to process all subscriptions. It will run until all subscriptions are
        unsubscribed from or, if `run_forever` is set to `True`, it will run
        indefinitely.

        :param run_forever: If `True`, the method will run indefinitely.
        :return: None
        """
        await self._handle_subscriptions(run_forever=run_forever)
