import json
import os
import time
from pathlib import Path

import requests


OPTIONS_PATH = Path("/data/options.json")
HA_API_URL = "http://supervisor/core/api"


def load_options() -> dict:
    if not OPTIONS_PATH.exists():
        raise FileNotFoundError(f"Options file not found: {OPTIONS_PATH}")

    with OPTIONS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_entity_state(entity_id: str, supervisor_token: str) -> dict | None:
    headers = {
        "Authorization": f"Bearer {supervisor_token}",
        "Content-Type": "application/json",
    }
    url = f"{HA_API_URL}/states/{entity_id}"

    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def main() -> None:
    options = load_options()
    target_entity = options.get("target_entity")
    tibber_api_key = options.get("tibber_api_key")
    supervisor_token = os.getenv("SUPERVISOR_TOKEN")

    if not target_entity:
        raise ValueError("Missing required option: target_entity")
    if not supervisor_token:
        raise EnvironmentError("Missing environment variable: SUPERVISOR_TOKEN")

    print("Add-on started.")
    print(f"Configured target_entity: {target_entity}")
    print(f"Tibber API key configured: {'yes' if tibber_api_key else 'no'}")

    initial_state = get_entity_state(target_entity, supervisor_token)
    if initial_state is None:
        print(f"Entity '{target_entity}' does not exist (initial check).")
    else:
        current_state = initial_state.get("state", "unknown")
        print(f"Current state of '{target_entity}': {current_state}")

    while True:
        try:
            state_data = get_entity_state(target_entity, supervisor_token)
            if state_data is None:
                print(f"Entity '{target_entity}' not found.")
            else:
                print(f"Entity '{target_entity}' exists. State: {state_data.get('state', 'unknown')}")
        except requests.RequestException as error:
            print(f"Error while checking entity '{target_entity}': {error}")

        time.sleep(10)


if __name__ == "__main__":
    main()
