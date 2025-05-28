"""
Configuration file for ProtoTrader Bot
"""

# Fee configuration
FEE_PERCENTAGE = 0.01  # 1% fee on all trades

# Fee recipient wallets for each chain
FEE_WALLETS = {
    'ETH': '0x742d35Cc6634C0532925a3b844Bc9e7595f6E123',  # Replace with your ETH wallet
    'SOL': '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM',  # Replace with your SOL wallet
    'TRX': 'TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW',  # Replace with your TRX wallet
}

# DEX Router addresses
DEX_ROUTERS = {
    'ETH': {
        'UNISWAP_V2': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        'UNISWAP_V3': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
        'SUSHISWAP': '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F',
    },
    'BSC': {
        'PANCAKESWAP_V2': '0x10ED43C718714eb63d5aA57B78B54704E256024E',
        'PANCAKESWAP_V3': '0x13f4EA83D0bd40E75C8222255bc855a974568Dd4',
    },
    'SOL': {
        'RAYDIUM': 'RaydiumV4',  # Program ID
        'ORCA': '9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP',
    },
    'TRX': {
        'SUNSWAP_V2': 'TKzxdSv2FZKQrEqkKVgp5DcwEXBEKMg2Ax',
        'SUNSWAP_V3': 'TFTg57jrXPasRiVfhTqUYt8Bfp2gJLJg8g',
    }
}

# WETH/WBNB/WSOL addresses
WRAPPED_TOKENS = {
    'ETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
    'BSC': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',  # WBNB
    'SOL': 'So11111111111111111111111111111111111111112',  # Wrapped SOL
    'TRX': 'TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR',  # WTRX
}

# Price APIs
PRICE_APIS = {
    'COINGECKO': 'https://api.coingecko.com/api/v3',
    'DEXSCREENER': 'https://api.dexscreener.com/latest/dex',
    'BIRDEYE': 'https://public-api.birdeye.so',
}

# Blockchain RPC endpoints
RPC_ENDPOINTS = {
    'ETH': [
        'https://eth.llamarpc.com',
        'https://rpc.ankr.com/eth',
        'https://ethereum.publicnode.com',
    ],
    'BSC': [
        'https://bsc-dataseed.binance.org/',
        'https://rpc.ankr.com/bsc',
        'https://bsc.publicnode.com',
    ],
    'SOL': [
        'https://api.mainnet-beta.solana.com',
        'https://solana-api.projectserum.com',
        'https://rpc.ankr.com/solana',
    ],
    'TRX': [
        'https://api.trongrid.io',
        'https://api.tronstack.io',
    ]
}

# Token security check parameters
SECURITY_CHECKS = {
    'MIN_LIQUIDITY_USD': 10000,  # Minimum liquidity in USD
    'MAX_BUY_TAX': 10,  # Maximum acceptable buy tax %
    'MAX_SELL_TAX': 10,  # Maximum acceptable sell tax %
    'MIN_HOLDERS': 50,  # Minimum number of holders
    'MAX_OWNER_PERCENTAGE': 20,  # Maximum % a single wallet can hold
}

# Trading limits
TRADING_LIMITS = {
    'MAX_TRADE_SIZE_ETH': 10,  # Maximum trade size in ETH
    'MAX_TRADE_SIZE_SOL': 1000,  # Maximum trade size in SOL
    'MAX_TRADE_SIZE_TRX': 100000,  # Maximum trade size in TRX
    'MIN_TRADE_SIZE_USD': 10,  # Minimum trade size in USD
}

# Monitoring settings
MONITORING = {
    'PRICE_CHECK_INTERVAL': 5,  # Seconds between price checks
    'TRANSACTION_TIMEOUT': 120,  # Seconds before transaction timeout
    'MAX_RETRY_ATTEMPTS': 3,  # Maximum retry attempts for failed transactions
}