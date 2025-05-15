import asyncio
import json
from _pydecimal import getcontext, Decimal
import aiohttp
from eth_abi import decode_abi
from eth_utils import decode_hex
from web3 import Web3
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


async def get_initial_prices(price_tracker, wss_url):
    """Получение начальных цен токенов через вызов RPC methods"""
    # Преобразуем WebSocket URL в HTTP URL для вызова RPC
    http_url = wss_url.replace('wss://', 'https://').replace('ws://', 'http://')
    w3 = Web3(Web3.HTTPProvider(http_url))
    
    # Получение начальных цен для каждого пула
    for pool_name, pool_info in POOLS.items():
        try:
            # Используем slot0 в Uniswap V3 пуле для получения текущей цены
            pool_contract = w3.eth.contract(
                address=w3.to_checksum_address(pool_info["address"]), 
                abi=[{"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"}]
            )
            
            # Вызов slot0 для получения текущей цены
            slot0 = pool_contract.functions.slot0().call()
            sqrt_price_x96 = Decimal(slot0[0])
            
            # Вычисление цены
            token0 = pool_info["token0"]
            token1 = pool_info["token1"]
            base_token = pool_info["token0"] if pool_info["token0"] in ["USDT", "DAI"] else pool_info["token1"]
            
            raw_price = (sqrt_price_x96 ** 2) / Decimal(2 ** 192)
            
            dec0 = TOKEN_DECIMALS[token0]
            dec1 = TOKEN_DECIMALS[token1]
            
            scale = Decimal(10) ** (dec0 - dec1)
            adjusted_price = raw_price * scale
            
            if base_token == token0:
                final_price = Decimal(1) / adjusted_price
            else:
                final_price = adjusted_price
                
            # Обновление цены в трекере
            price_tracker.update_price(pool_name, final_price)
            logger.info(f"📈 Начальная цена {pool_name}: 1 ETH ≈ {final_price:.6f} {base_token}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении начальной цены для {pool_name}: {e}")
