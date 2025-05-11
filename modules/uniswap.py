import asyncio
import json
from _pydecimal import getcontext, Decimal
import aiohttp
from eth_abi import decode_abi
from eth_utils import decode_hex
from config.config import WSS_URL, POOLS, SWAP_TOPIC

getcontext().prec = 36  # повышаем точность Decimal


async def subscribe_to_pool(pool_name, price_tracker):
    pool = POOLS[pool_name]
    base_token = pool["token0"] if pool["token0"] in ["USDT", "DAI"] else pool["token1"]

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WSS_URL) as ws:
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
            print(f"✅ Подписка на пул {pool_name} оформлена, ID: {subscription_id}")

            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if "params" in data:
                            log = data["params"]["result"]
                            price = decode_swap_event(log, pool, base_token)
                            price_tracker.update_price(pool_name, price)

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"❌ Ошибка WebSocket в пуле {pool_name}: {msg.data}")
                        break

            except asyncio.CancelledError:
                print(f"🛑 Подписка на пул {pool_name} остановлена вручную.")
            except Exception as e:
                print(f"⚠️ Неожиданная ошибка в {pool_name}: {type(e).__name__} — {e}")
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
                                print(f"📭 Отписка от пула {pool_name} успешна.")
                            else:
                                print(f"⚠️ Отписка от пула {pool_name} не удалась.")
                        else:
                            print(f"⚠️ Не удалось получить ответ на отписку от пула {pool_name}")
                except Exception as e:
                    print(f"❌ Ошибка при отписке от пула {pool_name}: {e}")


def decode_swap_event(log: dict, pool: dict, base_token: str) -> Decimal:
    """
    Декодирует событие Swap и возвращает цену base_token в ETH.
    """

    data = decode_hex(log["data"])

    amount0, amount1, sqrtPriceX96, liquidity, tick_bytes = decode_abi(
        ["int256", "int256", "uint160", "uint128", "bytes32"], data
    )

    sqrt_price = Decimal(sqrtPriceX96)
    raw_price = (sqrt_price ** 2) / Decimal(2 ** 192)

    token0 = pool["token0"]
    token1 = pool["token1"]

    if token0 == base_token:
        price = raw_price  # baseToken / ETH
    else:
        price = Decimal(1) / raw_price  # ETH / baseToken

    print(f"📊 Обновление цены в пуле {base_token}/ETH: {price}")
    return price
