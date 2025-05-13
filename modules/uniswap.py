import asyncio
import json
from _pydecimal import getcontext, Decimal
import aiohttp
from eth_abi import decode_abi
from eth_utils import decode_hex
from config.config import POOLS, SWAP_TOPIC, TOKEN_DECIMALS
from utils.logger import logger

getcontext().prec = 36


async def subscribe_to_pool(pool_name, price_tracker, wss_url):
    pool = POOLS[pool_name]
    base_token = pool["token0"] if pool["token0"] in ["USDT", "DAI"] else pool["token1"]

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(wss_url) as ws:
            subscribe_params = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": [
                    "logs",
                    {
                        "address": pool["address"],
                        "topics": [SWAP_TOPIC]
                    }
                ]
            }

            await ws.send_str(json.dumps(subscribe_params))
            subscription_response = await ws.receive()
            subscription_id = json.loads(subscription_response.data).get("result")
            logger.info(f"✅ Подписка на пул {pool_name} оформлена, ID: {subscription_id}\n")

            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if "params" in data:
                            log = data["params"]["result"]
                            price = decode_swap_event(log, pool, base_token)
                            price_tracker.update_price(pool_name, price)

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"❌ Ошибка WebSocket в пуле {pool_name}: {msg.data}")
                        break

            except asyncio.CancelledError:
                logger.error(f"🛑 Подписка на пул {pool_name} остановлена вручную.\n")
            except Exception as e:
                logger.warning(f"⚠️ Неожиданная ошибка в {pool_name}: {type(e).__name__} — {e}")
            finally:
                try:
                    if not ws.closed:
                        unsubscribe_params = {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "eth_unsubscribe",
                            "params": [subscription_id]
                        }
                        await ws.send_str(json.dumps(unsubscribe_params))
                        response = await ws.receive()

                        if response and response.type == aiohttp.WSMsgType.TEXT:
                            result = json.loads(response.data).get("result")
                            if result:
                                logger.info(f"📭 Отписка от пула {pool_name} успешна.\n")
                            else:
                                logger.warning(f"⚠️ Отписка от пула {pool_name} не удалась.\n")
                        else:
                            logger.warning(f"⚠️ Не удалось получить ответ на отписку от пула {pool_name}\n")
                except Exception as e:
                    logger.error(f"❌ Ошибка при отписке от пула {pool_name}: {e}")


def decode_swap_event(log: dict, pool: dict, base_token: str) -> Decimal:

    data = decode_hex(log["data"])
    _, _, sqrtPriceX96, _, _ = decode_abi(
        ["int256", "int256", "uint160", "uint128", "bytes32"], data
    )

    sqrt_price = Decimal(sqrtPriceX96)
    raw_price = (sqrt_price ** 2) / Decimal(2 ** 192)

    token0 = pool["token0"]
    token1 = pool["token1"]

    dec0 = TOKEN_DECIMALS[token0]
    dec1 = TOKEN_DECIMALS[token1]

    # поправка на decimals
    scale = Decimal(10) ** (dec0 - dec1)
    adjusted_price = raw_price * scale

    if base_token == token0:
        final_price = Decimal(1) / adjusted_price
    else:
        final_price = adjusted_price

    logger.info(f"📊 1 ETH ≈ {final_price:.6f} {base_token}")
    return final_price
