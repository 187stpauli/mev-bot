import asyncio
from modules.uniswap import subscribe_to_pool
from utils.price_tracker import PriceTracker
from config.config import THRESHOLD


async def main():
    price_tracker = PriceTracker(THRESHOLD)
    await asyncio.gather(
        subscribe_to_pool("USDT", price_tracker),
        subscribe_to_pool("DAI", price_tracker)
    )

if __name__ == "__main__":
    asyncio.run(main())

