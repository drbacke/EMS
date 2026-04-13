import requests

from agents.base_agent import BaseAgent

TIBBER_API_URL = "https://api.tibber.com/v1-beta/gql"


class GridAgent(BaseAgent):
    """Represents the public grid and sells energy."""

    def __init__(self, tibber_api_key: str | None = None, fallback_price: float = 0.0) -> None:
        super().__init__("GridAgent")
        self.tibber_api_key = tibber_api_key
        self.fallback_price = fallback_price

    def get_current_price(self) -> float:
        if not self.tibber_api_key:
            return self.fallback_price

        response = requests.post(
            TIBBER_API_URL,
            headers={
                "Authorization": f"Bearer {self.tibber_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "query": (
                    "{ viewer { homes { currentSubscription { priceInfo { current { total } } } } } }"
                )
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return float(
            data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["current"]["total"]
        )

    def tick(self) -> None:
        return
