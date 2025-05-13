POOLS = {
    "USDT": {
        "address": "0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36",  # WETH/USDT
        "token0": "WETH",
        "token1": "USDT"
    },
    "DAI": {
        "address": "0xc2e9f25be6257c210d7adf0d4cd6e3e881ba25f8",  # DAI/WETH
        "token0": "DAI",
        "token1": "WETH"
    }
}

# keccak256("Swap(address,uint256,uint256,uint256,uint256,address)")
SWAP_TOPIC = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"

TOKEN_DECIMALS = {
    "USDT": 6,
    "DAI": 18,
    "WETH": 18
}

THRESHOLD = 0.05
