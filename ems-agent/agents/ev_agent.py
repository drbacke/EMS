from datetime import datetime, timedelta

from adapters.ha_adapter import HomeAssistantAdapter
from agents.base_agent import BaseAgent


class EvAgent(BaseAgent):
    """EV buyer agent with forecast-aware bidding."""

    def __init__(
        self,
        name: str,
        entity_id: str,
        ha_adapter: HomeAssistantAdapter,
        forecast_entity: str,
        target_time: str,
        required_hours: float,
        max_price_limit: float,
    ) -> None:
        super().__init__(name)
        self.entity_id = entity_id
        self.ha_adapter = ha_adapter
        self.forecast_entity = forecast_entity
        self.target_time = target_time
        self.required_hours = required_hours
        self.max_price_limit = max_price_limit

    def tick(self) -> None:
        return

    def is_available(self) -> bool:
        return self.ha_adapter.get_entity_state(self.entity_id) is not None

    def _remaining_hours(self) -> float:
        try:
            now = datetime.now()
            hour, minute = [int(x) for x in self.target_time.split(":", 1)]
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target < now:
                target = target + timedelta(days=1)
            return max((target - now).total_seconds() / 3600.0, 0.0)
        except (ValueError, IndexError):
            return 0.0

    def get_max_bid(self) -> float:
        forecast_state = self.ha_adapter.get_entity_state(self.forecast_entity) if self.forecast_entity else None
        _forecast_attributes = (forecast_state or {}).get("attributes", {})
        # Placeholder for future advanced forecast parsing from attributes.
        remaining_hours = self._remaining_hours()
        if self.required_hours > remaining_hours:
            return self.max_price_limit
        return min(self.max_price_limit, 0.05)

    def on_trade_match(self, market_price: float) -> None:
        if market_price <= self.get_max_bid():
            self.ha_adapter.turn_on_entity(self.entity_id)
            print(f"[{self.name}] EV charging started at price {market_price:.4f}.")
        else:
            self.ha_adapter.turn_off_entity(self.entity_id)
            print(f"[{self.name}] EV charging paused at price {market_price:.4f}.")
