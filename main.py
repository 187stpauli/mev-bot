import asyncio
from config.configvalidator import ConfigValidator
from modules.uniswap import subscribe_to_pool, get_initial_prices
from utils.price_tracker import PriceTracker
from utils.logger import logger


async def main():
    try:
        logger.info("🚀 Запуск скрипта...\n")
        # Загрузка параметров
        logger.info("⚙️ Загрузка и валидация параметров...\n")
        validator = ConfigValidator("config/settings.json")
        settings = await validator.validate_config()
        threshold = settings["threshold"]
        wss_url = settings["wss_url"]
        price_tracker = PriceTracker(threshold)
        
        # Получение начальных цен
        logger.info("🔍 Получение начальных цен токенов...\n")
        await get_initial_prices(price_tracker, wss_url)
        
        await asyncio.gather(
            subscribe_to_pool("USDT", price_tracker, wss_url),
            subscribe_to_pool("DAI", price_tracker, wss_url)
        )
    except Exception as e:
        import traceback
        logger.error(f"🛑 Критическая ошибка: {type(e).__name__} — {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())

