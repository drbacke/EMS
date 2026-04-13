import requests

HA_API_URL = "http://supervisor/core/api"


class HomeAssistantAdapter:
    """Only this adapter talks to Home Assistant Supervisor API."""

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
        self.call_service("homeassistant", "turn_on", {"entity_id": entity_id})

    def turn_off_entity(self, entity_id: str) -> None:
        self.call_service("homeassistant", "turn_off", {"entity_id": entity_id})

    def call_service(self, domain: str, service: str, service_data: dict) -> None:
        response = requests.post(
            f"{HA_API_URL}/services/{domain}/{service}",
            headers=self._headers,
            json=service_data,
            timeout=10,
        )
        response.raise_for_status()
