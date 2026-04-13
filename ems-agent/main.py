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
        loaded = json.load(file)
    return {
        "grid_agent": loaded.get("grid_agent", {}),
        "devices": loaded.get("devices", []),
    }


def load_config_text() -> str:
    if not CONFIG_PATH.exists():
        return ""
    return CONFIG_PATH.read_text(encoding="utf-8")


def build_dynamic_consumers(
    device_configs: list[dict[str, Any]],
    ha_adapter: HomeAssistantAdapter,
) -> list[ConsumerAgent]:
    """Factory for runtime device -> agent creation."""
    consumers: list[ConsumerAgent] = []
    for index, config in enumerate(device_configs, start=1):
        label = str(config.get("name", "")).strip() or f"device_{index}"
        device_type = str(config.get("type", "generic")).strip().lower()
        entity = str(config.get("entity", "")).strip()
        max_price_raw = config.get("max_price", 0.0)

        if not entity:
            print(f"[Main] Ueberspringe Device #{index}: 'entity' fehlt.")
            continue

        try:
            max_price_limit = float(max_price_raw)
        except (TypeError, ValueError):
            print(f"[Main] Ueberspringe '{label}': max_price ungueltig.")
            continue

        if device_type == "ev_charger":
            # Future extension: instantiate EvAgent here.
            consumer = ConsumerAgent(
                name=f"ev_charger:{label}",
                entity_id=entity,
                max_price_limit=max_price_limit,
                ha_adapter=ha_adapter,
            )
        elif device_type == "heater":
            # Future extension: instantiate HeaterAgent here.
            consumer = ConsumerAgent(
                name=f"heater:{label}",
                entity_id=entity,
                max_price_limit=max_price_limit,
                ha_adapter=ha_adapter,
            )
        elif device_type == "battery":
            # Future extension: instantiate BatteryAgent here.
            consumer = ConsumerAgent(
                name=f"battery:{label}",
                entity_id=entity,
                max_price_limit=max_price_limit,
                ha_adapter=ha_adapter,
            )
        elif device_type == "generic":
            consumer = ConsumerAgent(
                name=f"generic:{label}",
                entity_id=entity,
                max_price_limit=max_price_limit,
                ha_adapter=ha_adapter,
            )
        else:
            print(f"[Main] Unbekannter device type '{device_type}' bei '{label}'.")
            continue

        consumers.append(consumer)
    return consumers


def main() -> None:
    config_text = load_config_text()
    options = load_options()

    supervisor_token = os.getenv("SUPERVISOR_TOKEN")
    grid_agent_cfg = options.get("grid_agent", {})
    devices_cfg = options.get("devices", [])

    if not supervisor_token:
        raise EnvironmentError("Missing environment variable: SUPERVISOR_TOKEN")
    if not isinstance(grid_agent_cfg, dict):
        raise ValueError("Invalid option: 'grid_agent' must be an object")
    if not isinstance(devices_cfg, list):
        raise ValueError("Invalid option: 'devices' must be a list")

    provider = str(grid_agent_cfg.get("provider", "simulation")).strip().lower()
    api_key = str(grid_agent_cfg.get("api_key", "")).strip()

    ha_adapter = HomeAssistantAdapter(supervisor_token)
    if provider == "tibber":
        grid_agent = GridAgent(tibber_api_key=api_key or None)
    elif provider == "simulation":
        grid_agent = GridAgent(tibber_api_key=None)
    else:
        print(f"[Main] Unbekannter grid_agent.provider '{provider}', nutze simulation.")
        grid_agent = GridAgent(tibber_api_key=None)
    broker = EnergyBroker(seller=grid_agent)

    consumers = build_dynamic_consumers(devices_cfg, ha_adapter)
    for consumer in consumers:
        broker.register_buyer(consumer)

    print("EMS Entrypoint gestartet.")
    print(f"Config geladen: {'ja' if config_text else 'nein'}")
    print(f"Grid provider: {provider}")
    print(f"Devices: {len(devices_cfg)}")
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
