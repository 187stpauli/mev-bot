
class PriceTracker:
    def __init__(self, threshold=0.02):
        self.prices = {}
        self.threshold = threshold

    def update_price(self, token, price):
        self.prices[token] = price
        if "USDT" in self.prices and "DAI" in self.prices:
            self.check_spread()

    def check_spread(self):
        usdt_price = self.prices["USDT"]
        dai_price = self.prices["DAI"]
        spread = abs(usdt_price - dai_price) / ((usdt_price + dai_price) / 2)
        if spread >= self.threshold:
            print(f"Arbitrage opportunity detected! Spread: {spread*100:.2f}%")
