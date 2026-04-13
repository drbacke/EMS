from dataclasses import dataclass

from agents.consumer_agent import ConsumerAgent
from agents.grid_agent import GridAgent


@dataclass
class MatchResult:
    matched: bool
    market_price: float
    max_bid: float


class EnergyBroker:
    """Market broker that only matches bids and offers."""

    def __init__(self, seller: GridAgent, buyer: ConsumerAgent) -> None:
        self.seller = seller
        self.buyer = buyer

    def match(self) -> MatchResult:
        market_price = self.seller.get_current_price()
        max_bid = self.buyer.get_max_bid()
        return MatchResult(
            matched=market_price < max_bid,
            market_price=market_price,
            max_bid=max_bid,
        )
