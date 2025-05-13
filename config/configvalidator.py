from urllib.parse import urlparse
import aiohttp
import logging
import json

logger = logging.getLogger(__name__)


class ConfigValidator:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config_data = self.load_config()

    def load_config(self) -> dict:
        """Загружает конфигурационный файл"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            logging.error(f"❗️ Файл конфигурации {self.config_path} не найден.")
            exit(1)
        except json.JSONDecodeError:
            logging.error(f"❗️ Ошибка разбора JSON в файле конфигурации {self.config_path}.")
            exit(1)

    async def validate_config(self) -> dict:
        """Валидация всех полей конфигурации"""
        try:

            await self.validate_required_keys()

            if "threshold" not in self.config_data:
                logging.error("❗️ Ошибка: Отсутствует 'threshold' в конфигурации.")
                exit(1)

            if "wss_url" not in self.config_data:
                logging.error("❗️ Ошибка: Отсутствует 'wss_url' в конфигурации.")
                exit(1)

            await self.validate_threshold(self.config_data["threshold"])
            await self.validate_wss_url(self.config_data["wss_url"])

            return self.config_data

        except Exception as e:
            logger.error(f"🛑 Критическая ошибка: {e}")

    async def validate_required_keys(self):
        required_keys = [
            "threshold",
            "wss_url"
        ]

        for key in required_keys:
            if key not in self.config_data:
                logging.error(f"❗️ Ошибка: отсутствует обязательный ключ '{key}' в settings.json")
                exit(1)

    @staticmethod
    async def validate_threshold(threshold: float) -> None:

        if not threshold > 0:
            logging.error("❗️ Ошибка: Порог срабатывания меньше допустимого! Введите значение больше 0.")
            exit(1)

    @staticmethod
    def is_valid_wss_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("wss", "ws") and bool(parsed.netloc)
        except Exception as e:
            print(e)
            return False

    @staticmethod
    async def test_ws_connection(url: str, timeout: int = 5) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url, timeout=timeout) as ws:
                    await ws.close()
                    return True
        except Exception as e:
            print(e)
            return False

    async def validate_wss_url(self, wss_url: str) -> None:

        if not self.is_valid_wss_url(wss_url):
            logging.error("❌ URL имеет неверный формат.")
            exit(1)

        logging.info("⏳ Проверка подключения к WebSocket...")
        if await self.test_ws_connection(wss_url):
            logging.info("✅ WebSocket соединение установлено.\n")

        else:
            logging.error("❌ Не удалось подключиться к WebSocket.")
            exit(1)
