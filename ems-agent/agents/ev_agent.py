from adapters.ha_adapter import HomeAssistantAdapter
from agents.consumer_agent import ConsumerAgent


class EvAgent(ConsumerAgent):
    """Specialized EV buyer agent with dynamic bidding support."""

    def __init__(
        self,
        name: str,
        entity_id: str,
        max_price_limit: float,
        ha_adapter: HomeAssistantAdapter,
    ) -> None:
        super().__init__(
            name=name,
            entity_id=entity_id,
            max_price_limit=max_price_limit,
            ha_adapter=ha_adapter,
        )

    def calculate_dynamic_bid(self, simulated_price_forecast: list[float]) -> float:
        """
        Calculate a dynamic bid from a simulated future price list.
        For MVP: choose the cheapest forecast price, capped by max_price_limit.
        """
        if not simulated_price_forecast:
            return self.max_price_limit
        return min(min(simulated_price_forecast), self.max_price_limit)
