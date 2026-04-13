import json
import os
import time
from pathlib import Path

import requests

from adapters.ha_adapter import HomeAssistantAdapter
from agents.consumer_agent import ConsumerAgent
from agents.grid_agent import GridAgent
from core.broker import EnergyBroker

OPTIONS_PATH = Path("/data/options.json")
CONFIG_PATH = Path(__file__).with_name("config.yaml")
DEFAULT_MAX_PRICE_LIMIT = 0.30


def load_options() -> dict:
    if not OPTIONS_PATH.exists():
        raise FileNotFoundError(f"Options file not found: {OPTIONS_PATH}")
    with OPTIONS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_config_text() -> str:
    if not CONFIG_PATH.exists():
        return ""
    return CONFIG_PATH.read_text(encoding="utf-8")


def main() -> None:
    config_text = load_config_text()
    options = load_options()

    supervisor_token = os.getenv("SUPERVISOR_TOKEN")
    target_entity = options.get("target_entity")
    tibber_api_key = options.get("tibber_api_key")
    max_price_limit = float(options.get("max_price_limit", DEFAULT_MAX_PRICE_LIMIT))

    if not target_entity:
        raise ValueError("Missing required option: target_entity")
    if not supervisor_token:
        raise EnvironmentError("Missing environment variable: SUPERVISOR_TOKEN")

    ha_adapter = HomeAssistantAdapter(supervisor_token)
    grid_agent = GridAgent(tibber_api_key=tibber_api_key)
    consumer_agent = ConsumerAgent(
        entity_id=target_entity,
        max_price_limit=max_price_limit,
        ha_adapter=ha_adapter,
    )
    broker = EnergyBroker(seller=grid_agent, buyer=consumer_agent)

    print("EMS Entrypoint gestartet.")
    print(f"Config geladen: {'ja' if config_text else 'nein'}")
    print(f"Target-Entity: {target_entity}")
    print(f"Max-Preislimit: {max_price_limit}")

    while True:
        try:
            if not consumer_agent.is_available():
                print(f"[Main] Entitaet '{target_entity}' nicht gefunden.")
            else:
                result = broker.match()
                print(
                    f"[Main] Marktpreis={result.market_price:.4f}, "
                    f"MaxBid={result.max_bid:.4f}, Match={result.matched}"
                )
                if result.matched:
                    consumer_agent.on_trade_match(result.market_price)
        except (requests.RequestException, ValueError, KeyError, IndexError) as error:
            print(f"[Main] Fehler im Loop: {error}")
        time.sleep(10)


if __name__ == "__main__":
    main()
