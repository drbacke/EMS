from dataclasses import dataclass

from agents.consumer_agent import ConsumerAgent
from agents.grid_agent import GridAgent


@dataclass
class MatchResult:
    buyer_name: str
    buyer_entity: str
    matched: bool
    market_price: float
    max_bid: float


class EnergyBroker:
    """Market broker that only matches bids and offers."""

    def __init__(self, seller: GridAgent) -> None:
        self.seller = seller
        self.buyers: list[ConsumerAgent] = []

    def register_buyer(self, buyer: ConsumerAgent) -> None:
        self.buyers.append(buyer)

    def match_all(self) -> list[MatchResult]:
        market_price = self.seller.get_current_price()
        results: list[MatchResult] = []
        for buyer in self.buyers:
            max_bid = buyer.get_max_bid()
            results.append(
                MatchResult(
                    buyer_name=buyer.name,
                    buyer_entity=buyer.entity_id,
                    matched=market_price < max_bid,
                    market_price=market_price,
                    max_bid=max_bid,
                )
            )
        return results
