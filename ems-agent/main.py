import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from adapters.ha_adapter import HomeAssistantAdapter
from agents.consumer_agent import ConsumerAgent
from agents.ev_agent import EvAgent
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
        "devices": loaded.get("devices", []),
    }


def load_config_text() -> str:
    if not CONFIG_PATH.exists():
        return ""
    return CONFIG_PATH.read_text(encoding="utf-8")


def build_dynamic_agents(
    device_configs: list[dict[str, Any]],
    ha_adapter: HomeAssistantAdapter,
    broker: EnergyBroker,
) -> list[object]:
    """Factory for runtime device -> agent creation and broker registration."""
    buyers: list[object] = []
    for index, config in enumerate(device_configs, start=1):
        label = str(config.get("name", "")).strip() or f"device_{index}"
        device_type = str(config.get("type", "generic")).strip().lower()
        entity = str(config.get("entity", "")).strip()
        max_price_raw = config.get("max_price", 0.0)
        api_key = str(config.get("api_key", "")).strip()

        if device_type != "grid" and not entity:
            print(f"[Main] Ueberspringe Device #{index}: 'entity' fehlt.")
            continue

        if device_type == "grid":
            # Future extension: choose specific grid provider implementation.
            grid_agent = GridAgent(tibber_api_key=api_key or None)
            broker.register_seller(grid_agent)
            continue

        try:
            max_price_limit = float(max_price_raw)
        except (TypeError, ValueError):
            print(f"[Main] Ueberspringe '{label}': max_price ungueltig.")
            continue

        if device_type == "ev_charger":
            forecast_entity = str(config.get("forecast_entity", "")).strip()
            target_time = str(config.get("target_time", "07:00")).strip()
            required_hours_raw = config.get("required_hours", 0.0)
            try:
                required_hours = float(required_hours_raw)
            except (TypeError, ValueError):
                required_hours = 0.0

            consumer = EvAgent(
                name=f"ev_charger:{label}",
                entity_id=entity,
                ha_adapter=ha_adapter,
                forecast_entity=forecast_entity,
                target_time=target_time,
                required_hours=required_hours,
                max_price_limit=max_price_limit,
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

        broker.register_buyer(consumer)
        buyers.append(consumer)
    return buyers


def main() -> None:
    config_text = load_config_text()
    options = load_options()

    supervisor_token = os.getenv("SUPERVISOR_TOKEN")
    devices_cfg = options.get("devices", [])

    if not supervisor_token:
        raise EnvironmentError("Missing environment variable: SUPERVISOR_TOKEN")
    if not isinstance(devices_cfg, list):
        raise ValueError("Invalid option: 'devices' must be a list")

    ha_adapter = HomeAssistantAdapter(supervisor_token)
    broker = EnergyBroker()
    consumers = build_dynamic_agents(devices_cfg, ha_adapter, broker)

    print("EMS Entrypoint gestartet.")
    print(f"Config geladen: {'ja' if config_text else 'nein'}")
    print(f"Devices: {len(devices_cfg)}")
    print(f"Seller-Agenten: {len(broker.sellers)}")
    print(f"Konfigurierte Agenten: {len(consumers)}")

    if not consumers:
        print("[Main] Keine Agenten konfiguriert. Starte im Leerlauf.")
    if not broker.sellers:
        print("[Main] Kein Grid-Seller konfiguriert. Es werden keine Matches erstellt.")

    while True:
        try:
            if not consumers:
                time.sleep(LOOP_INTERVAL_SECONDS)
                continue

            results = broker.match_all()
            if not results:
                time.sleep(LOOP_INTERVAL_SECONDS)
                continue
            for buyer, result in zip(consumers, results):
                if not buyer.is_available():
                    print(f"[Main] Entitaet '{buyer.entity_id}' nicht gefunden.")
                    continue

                print(
                    f"[Main] {result.buyer_name} | Marktpreis={result.market_price:.4f}, "
                    f"MaxBid={result.max_bid:.4f}, Match={result.matched}"
                )
                if result.matched:
                    buyer.on_trade_match(result.market_price)
        except (requests.RequestException, ValueError, KeyError, IndexError) as error:
            print(f"[Main] Fehler im Loop: {error}")
        time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
