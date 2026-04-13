from agents.base_agent import BaseAgent
from adapters.ha_adapter import HomeAssistantAdapter


class ConsumerAgent(BaseAgent):
    """Represents a controllable appliance that buys energy."""

    def __init__(
        self,
        name: str,
        entity_id: str,
        max_price_limit: float,
        ha_adapter: HomeAssistantAdapter,
    ) -> None:
        super().__init__(name)
        self.entity_id = entity_id
        self.max_price_limit = max_price_limit
        self.ha_adapter = ha_adapter

    def is_available(self) -> bool:
        return self.ha_adapter.get_entity_state(self.entity_id) is not None

    def get_max_bid(self) -> float:
        return self.max_price_limit

    def on_trade_match(self, market_price: float) -> None:
        self.ha_adapter.turn_on_entity(self.entity_id)
        print(
            f"[{self.name}] Trade accepted at {market_price:.4f}. "
            f"'{self.entity_id}' switched on."
        )

    def tick(self) -> None:
        return
