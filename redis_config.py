"""
Redis Configuration
"""

import os
from typing import Dict, Any

# Redis connection settings
REDIS_CONFIG: Dict[str, Any] = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'password': os.getenv('REDIS_PASSWORD'),
    'max_connections': 50,
    'decode_responses': False,
}

# Cache TTL settings (in seconds)
CACHE_TTL = {
    'price': 30,  # Token prices
    'liquidity': 300,  # Liquidity data
    'gas': 30,  # Gas prices
    'session': 3600,  # User sessions
    'transaction': 86400,  # Transaction data
    'security_scan': 1800,  # Security scan results
    'arbitrage_scan': 300,  # Arbitrage scan markers
}

# Queue settings
QUEUE_CONFIG = {
    'trading': {
        'workers': 5,
        'max_retries': 3,
        'retry_delay': 5,
    },
    'notification': {
        'workers': 2,
        'max_retries': 3,
        'retry_delay': 2,
    },
    'analytics': {
        'workers': 2,
        'max_retries': 5,
        'retry_delay': 10,
    },
}

# Rate limiting settings
RATE_LIMITS = {
    'fee_transactions': {
        'limit': 10,
        'window': 60,  # 10 fee transactions per minute
    },
    'trades_per_user': {
        'limit': 50,
        'window': 3600,  # 50 trades per hour per user
    },
    'api_calls': {
        'limit': 100,
        'window': 60,  # 100 API calls per minute
    },
}

# Redis key patterns
KEY_PATTERNS = {
    'price': 'price:{chain}:{token}',
    'liquidity': 'liquidity:{chain}:{pair}',
    'gas': 'gas:{chain}',
    'session': 'session:{user_id}',
    'transaction': 'tx:{tx_hash}',
    'trade': 'trade:{trade_id}',
    'active_trades': 'active_trades:{user_id}',
    'task': 'task:{task_id}',
    'queue': 'queue:{queue_name}:{priority}',
    'rate_limit': 'rate:{key}',
    'arbitrage_scan': 'arb_scan:{chain}:{token}',
    'security_scan': 'security:{chain}:{token}',
}