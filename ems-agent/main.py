import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests

OPTIONS_PATH = Path("/data/options.json")
HA_API_URL = "http://supervisor/core/api"
TIBBER_API_URL = "https://api.tibber.com/v1-beta/gql"
DEFAULT_MAX_PRICE_LIMIT = 0.30


def load_options() -> dict:
    if not OPTIONS_PATH.exists():
        raise FileNotFoundError(f"Options file not found: {OPTIONS_PATH}")
    with OPTIONS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


class HomeAssistantApi:
    def __init__(self, supervisor_token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {supervisor_token}",
            "Content-Type": "application/json",
        }

    def get_entity_state(self, entity_id: str) -> dict | None:
        response = requests.get(
            f"{HA_API_URL}/states/{entity_id}",
            headers=self._headers,
            timeout=10,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def turn_on_entity(self, entity_id: str) -> None:
        payload = {"entity_id": entity_id}
        response = requests.post(
            f"{HA_API_URL}/services/homeassistant/turn_on",
            headers=self._headers,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()


class BaseAgent(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def tick(self) -> None:
        """Runs one agent cycle."""


class GridAgent(BaseAgent):
    def __init__(self, tibber_api_key: str | None = None) -> None:
        super().__init__("GridAgent")
        self.tibber_api_key = tibber_api_key

    def get_current_price(self) -> float:
        if not self.tibber_api_key:
            print("[GridAgent] Kein Tibber-Key gesetzt. Nutze Defaultpreis 0.0 EUR/kWh.")
            return 0.0

        query = {
            "query": (
                "{ viewer { homes { currentSubscription { priceInfo { current { total } } } } } }"
            )
        }
        headers = {
            "Authorization": f"Bearer {self.tibber_api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(TIBBER_API_URL, headers=headers, json=query, timeout=10)
        response.raise_for_status()

        data = response.json()
        return float(
            data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["current"]["total"]
        )

    def tick(self) -> None:
        # This agent provides price data and needs no own loop action yet.
        return


class ApplianceAgent(BaseAgent):
    def __init__(self, ha_api: HomeAssistantApi, entity_id: str, max_price_limit: float) -> None:
        super().__init__("ApplianceAgent")
        self.ha_api = ha_api
        self.entity_id = entity_id
        self.max_price_limit = max_price_limit

    def exists(self) -> bool:
        return self.ha_api.get_entity_state(self.entity_id) is not None

    def turn_on(self) -> None:
        self.ha_api.turn_on_entity(self.entity_id)
        print(f"[ApplianceAgent] '{self.entity_id}' wurde eingeschaltet.")

    def tick(self) -> None:
        # This agent is commanded by broker decisions.
        return


class EnergyBroker:
    def __init__(self, grid_agent: GridAgent, appliance_agent: ApplianceAgent) -> None:
        self.grid_agent = grid_agent
        self.appliance_agent = appliance_agent

    def tick(self) -> None:
        if not self.appliance_agent.exists():
            print(f"[Broker] Entitaet '{self.appliance_agent.entity_id}' nicht gefunden.")
            return

        current_price = self.grid_agent.get_current_price()
        max_price = self.appliance_agent.max_price_limit
        print(f"[Broker] Preisvergleich: Grid={current_price:.4f}, Limit={max_price:.4f}")

        if current_price < max_price:
            print("[Broker] Preis unter Limit -> schalte ein.")
            self.appliance_agent.turn_on()
        else:
            print("[Broker] Preis ueber Limit -> bleibe aus.")


def main() -> None:
    options = load_options()
    supervisor_token = os.getenv("SUPERVISOR_TOKEN")
    target_entity = options.get("target_entity")
    tibber_api_key = options.get("tibber_api_key")
    max_price_limit = float(options.get("max_price_limit", DEFAULT_MAX_PRICE_LIMIT))

    if not target_entity:
        raise ValueError("Missing required option: target_entity")
    if not supervisor_token:
        raise EnvironmentError("Missing environment variable: SUPERVISOR_TOKEN")

    ha_api = HomeAssistantApi(supervisor_token)
    grid_agent = GridAgent(tibber_api_key=tibber_api_key)
    appliance_agent = ApplianceAgent(
        ha_api=ha_api,
        entity_id=target_entity,
        max_price_limit=max_price_limit,
    )
    broker = EnergyBroker(grid_agent=grid_agent, appliance_agent=appliance_agent)

    print("EMS Multi-Agent Add-on gestartet.")
    print(f"Target-Entity: {target_entity}")
    print(f"Max-Preislimit: {max_price_limit}")

    while True:
        try:
            broker.tick()
        except (requests.RequestException, KeyError, ValueError, IndexError) as error:
            print(f"[Broker] Fehler im Agentenlauf: {error}")
        time.sleep(10)


if __name__ == "__main__":
    main()
