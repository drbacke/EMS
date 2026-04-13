import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from adapters.ha_adapter import HomeAssistantAdapter
from agents.consumer_agent import ConsumerAgent
from agents.grid_agent import GridAgent
from core.broker import EnergyBroker

OPTIONS_PATH = Path("/data/options.json")
CONFIG_PATH = Path(__file__).with_name("config.yaml")
LOOP_INTERVAL_SECONDS = 10


def load_options() -> dict:
    if not OPTIONS_PATH.exists():
        raise FileNotFoundError(f"Options file not found: {OPTIONS_PATH}")
    with OPTIONS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_config_text() -> str:
    if not CONFIG_PATH.exists():
        return ""
    return CONFIG_PATH.read_text(encoding="utf-8")


def build_dynamic_consumers(
    agent_configs: list[dict[str, Any]],
    ha_adapter: HomeAssistantAdapter,
) -> list[ConsumerAgent]:
    consumers: list[ConsumerAgent] = []
    for index, config in enumerate(agent_configs, start=1):
        agent_type = str(config.get("name", "")).strip().lower()
        entity = str(config.get("entity", "")).strip()
        max_price_raw = config.get("max_price", 0.0)

        if not entity:
            print(f"[Main] Ueberspringe Agent #{index}: 'entity' fehlt.")
            continue

        if agent_type in {"consumer", "consumeragent", ""}:
            try:
                max_price = float(max_price_raw)
            except (TypeError, ValueError):
                print(f"[Main] Ueberspringe Agent '{entity}': max_price ungueltig.")
                continue

            consumers.append(
                ConsumerAgent(
                    name=f"ConsumerAgent:{entity}",
                    entity_id=entity,
                    max_price_limit=max_price,
                    ha_adapter=ha_adapter,
                )
            )
        else:
            print(f"[Main] Unbekannter Agent-Typ '{agent_type}' fuer Entity '{entity}'.")
    return consumers


def main() -> None:
    config_text = load_config_text()
    options = load_options()

    supervisor_token = os.getenv("SUPERVISOR_TOKEN")
    tibber_api_key = options.get("tibber_api_key")
    agent_configs = options.get("agents", [])

    if not supervisor_token:
        raise EnvironmentError("Missing environment variable: SUPERVISOR_TOKEN")
    if not isinstance(agent_configs, list):
        raise ValueError("Invalid option: 'agents' must be a list")

    ha_adapter = HomeAssistantAdapter(supervisor_token)
    grid_agent = GridAgent(tibber_api_key=tibber_api_key)
    broker = EnergyBroker(seller=grid_agent)

    consumers = build_dynamic_consumers(agent_configs, ha_adapter)
    for consumer in consumers:
        broker.register_buyer(consumer)

    print("EMS Entrypoint gestartet.")
    print(f"Config geladen: {'ja' if config_text else 'nein'}")
    print(f"Konfigurierte Agenten: {len(consumers)}")

    if not consumers:
        print("[Main] Keine Agenten konfiguriert. Starte im Leerlauf.")

    while True:
        try:
            if not consumers:
                time.sleep(LOOP_INTERVAL_SECONDS)
                continue

            results = broker.match_all()
            for consumer, result in zip(consumers, results):
                if not consumer.is_available():
                    print(f"[Main] Entitaet '{consumer.entity_id}' nicht gefunden.")
                    continue

                print(
                    f"[Main] {result.buyer_name} | Marktpreis={result.market_price:.4f}, "
                    f"MaxBid={result.max_bid:.4f}, Match={result.matched}"
                )
                if result.matched:
                    consumer.on_trade_match(result.market_price)
        except (requests.RequestException, ValueError, KeyError, IndexError) as error:
            print(f"[Main] Fehler im Loop: {error}")
        time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
