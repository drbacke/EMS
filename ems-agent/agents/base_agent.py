from abc import ABC, abstractmethod


class BaseAgent(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def tick(self) -> None:
        """Runs one agent cycle."""
