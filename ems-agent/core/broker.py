from dataclasses import dataclass

from agents.consumer_agent import ConsumerAgent


@dataclass
class MatchResult:
    buyer_name: str
    buyer_entity: str
    matched: bool
    market_price: float
    max_bid: float


class EnergyBroker:
    """Market broker that only matches bids and offers."""

    def __init__(self) -> None:
        self.sellers: list[object] = []
        self.buyers: list[ConsumerAgent] = []

    def register_seller(self, agent: object) -> None:
        self.sellers.append(agent)

    def register_buyer(self, buyer: ConsumerAgent) -> None:
        self.buyers.append(buyer)

    def match_all(self) -> list[MatchResult]:
        if not self.sellers:
            print("[Broker] Warnung: Keine Seller registriert, Match wird uebersprungen.")
            return []

        seller_prices: list[float] = []
        for seller in self.sellers:
            if not hasattr(seller, "get_current_price"):
                continue
            try:
                seller_prices.append(float(seller.get_current_price()))
            except (TypeError, ValueError):
                continue

        if not seller_prices:
            return []

        market_price = min(seller_prices)
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
