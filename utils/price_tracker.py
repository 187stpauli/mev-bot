from utils.logger import logger


class PriceTracker:
    def __init__(self, threshold):
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
        
        # Проверка на превышение порога
        if spread >= self.threshold:
            if usdt_price > dai_price:
                direction = "USDT/ETH выше, чем DAI/ETH"
            elif dai_price > usdt_price:
                direction = "DAI/ETH выше, чем USDT/ETH"
            else:
                direction = "цены равны"

            logger.info(f"💰 Найден арбитраж: {direction}, разница составляет {spread * 100:.2f}%\n")
