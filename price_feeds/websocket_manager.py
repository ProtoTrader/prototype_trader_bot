"""
WebSocket Manager - Real-time price feeds from multiple sources
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Callable, Optional, Set
from datetime import datetime
import aiohttp
from decimal import Decimal

logger = logging.getLogger(__name__)


class PriceFeedManager:
    """Manages WebSocket connections for real-time price feeds"""
    
    def __init__(self):
        self.connections = {}
        self.subscribers = {}  # token -> set of callbacks
        self.price_cache = {}
        self.running = False
        self.tasks = []
        
        # DexScreener WebSocket endpoint
        self.dexscreener_ws = "wss://api.dexscreener.com/v1/ws"
        
        # Other price feed endpoints
        self.endpoints = {
            'dexscreener': {
                'ws': 'wss://api.dexscreener.com/v1/ws',
                'api': 'https://api.dexscreener.com/latest/dex'
            },
            'birdeye': {
                'ws': 'wss://public-api.birdeye.so/socket',
                'api': 'https://public-api.birdeye.so/public'
            },
            'defined': {
                'ws': 'wss://api.defined.fi/ws',
                'api': 'https://api.defined.fi'
            }
        }
    
    async def start(self):
        """Start price feed manager"""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting price feed manager...")
        
        # Start WebSocket connections
        self.tasks = [
            asyncio.create_task(self._dexscreener_handler()),
            asyncio.create_task(self._price_aggregator()),
            asyncio.create_task(self._health_monitor())
        ]
    
    async def stop(self):
        """Stop price feed manager"""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Close all connections
        for conn in self.connections.values():
            if conn and not conn.closed:
                await conn.close()
        
        logger.info("Price feed manager stopped")
    
    def subscribe_token(self, chain: str, token_address: str, 
                       callback: Callable[[Dict], None]) -> str:
        """Subscribe to price updates for a token"""
        key = f"{chain}:{token_address.lower()}"
        
        if key not in self.subscribers:
            self.subscribers[key] = set()
        
        # Generate subscription ID
        sub_id = f"{key}:{id(callback)}"
        self.subscribers[key].add((sub_id, callback))
        
        logger.info(f"Subscribed to {key}")
        
        # Send initial cached price if available
        if key in self.price_cache:
            try:
                callback(self.price_cache[key])
            except Exception as e:
                logger.error(f"Callback error: {e}")
        
        return sub_id
    
    def unsubscribe(self, subscription_id: str):
        """Unsubscribe from price updates"""
        parts = subscription_id.rsplit(':', 1)
        if len(parts) == 2:
            key = parts[0]
            if key in self.subscribers:
                self.subscribers[key] = {
                    (sid, cb) for sid, cb in self.subscribers[key] 
                    if sid != subscription_id
                }
                if not self.subscribers[key]:
                    del self.subscribers[key]
    
    async def _dexscreener_handler(self):
        """Handle DexScreener WebSocket connection"""
        while self.running:
            try:
                async with websockets.connect(self.dexscreener_ws) as ws:
                    self.connections['dexscreener'] = ws
                    logger.info("Connected to DexScreener WebSocket")
                    
                    # Subscribe to pairs
                    await self._subscribe_dexscreener_pairs(ws)
                    
                    # Handle messages
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            await self._process_dexscreener_data(data)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON from DexScreener: {message}")
                        except Exception as e:
                            logger.error(f"Error processing DexScreener data: {e}")
                            
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"DexScreener WebSocket error: {e}")
                await asyncio.sleep(5)  # Reconnect delay
            except Exception as e:
                logger.error(f"DexScreener handler error: {e}")
                await asyncio.sleep(10)
    
    async def _subscribe_dexscreener_pairs(self, ws):
        """Subscribe to token pairs on DexScreener"""
        # Subscribe to all tokens we're tracking
        for key in self.subscribers.keys():
            chain, address = key.split(':')
            
            # Map chain names to DexScreener format
            chain_map = {
                'ETH': 'ethereum',
                'BSC': 'bsc',
                'SOL': 'solana'
            }
            
            if chain in chain_map:
                sub_message = {
                    'type': 'subscribe',
                    'channel': 'pair',
                    'chainId': chain_map[chain],
                    'tokenAddress': address
                }
                await ws.send(json.dumps(sub_message))
    
    async def _process_dexscreener_data(self, data: Dict):
        """Process DexScreener price data"""
        if data.get('type') == 'pair':
            pair_data = data.get('pair', {})
            
            # Extract token info
            chain_id = pair_data.get('chainId', '')
            base_token = pair_data.get('baseToken', {})
            
            # Map back to our chain format
            chain_map = {
                'ethereum': 'ETH',
                'bsc': 'BSC',
                'solana': 'SOL'
            }
            
            chain = chain_map.get(chain_id, chain_id.upper())
            token_address = base_token.get('address', '').lower()
            
            if not chain or not token_address:
                return
            
            key = f"{chain}:{token_address}"
            
            # Extract price data
            price_data = {
                'source': 'dexscreener',
                'chain': chain,
                'token_address': token_address,
                'symbol': base_token.get('symbol', ''),
                'name': base_token.get('name', ''),
                'price_usd': float(pair_data.get('priceUsd', 0)),
                'price_native': float(pair_data.get('priceNative', 0)),
                'liquidity_usd': float(pair_data.get('liquidity', {}).get('usd', 0)),
                'volume_24h': float(pair_data.get('volume', {}).get('h24', 0)),
                'price_change_24h': float(pair_data.get('priceChange', {}).get('h24', 0)),
                'txns_24h': pair_data.get('txns', {}).get('h24', {}),
                'pair_address': pair_data.get('pairAddress', ''),
                'dex': pair_data.get('dexId', ''),
                'timestamp': datetime.now(),
                'raw_data': pair_data
            }
            
            # Update cache
            self.price_cache[key] = price_data
            
            # Notify subscribers
            await self._notify_subscribers(key, price_data)
    
    async def _notify_subscribers(self, key: str, price_data: Dict):
        """Notify all subscribers of price update"""
        if key in self.subscribers:
            # Create tasks for all callbacks
            tasks = []
            for sub_id, callback in self.subscribers[key]:
                task = asyncio.create_task(self._safe_callback(callback, price_data))
                tasks.append(task)
            
            # Wait for all callbacks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_callback(self, callback: Callable, data: Dict):
        """Safely execute callback"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    async def _price_aggregator(self):
        """Aggregate prices from multiple sources"""
        while self.running:
            try:
                # Fetch prices from APIs for tokens without WebSocket data
                for key in self.subscribers.keys():
                    if key not in self.price_cache or \
                       (datetime.now() - self.price_cache[key]['timestamp']).seconds > 60:
                        chain, address = key.split(':')
                        await self._fetch_price_from_api(chain, address)
                
                await asyncio.sleep(30)  # Aggregate every 30 seconds
                
            except Exception as e:
                logger.error(f"Price aggregator error: {e}")
                await asyncio.sleep(60)
    
    async def _fetch_price_from_api(self, chain: str, token_address: str):
        """Fetch price from REST API as fallback"""
        try:
            # DexScreener API
            chain_map = {
                'ETH': 'ethereum',
                'BSC': 'bsc', 
                'SOL': 'solana'
            }
            
            if chain not in chain_map:
                return
            
            url = f"{self.endpoints['dexscreener']['api']}/tokens/{token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        
                        if pairs:
                            # Use pair with highest liquidity
                            best_pair = max(pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                            
                            # Process as if from WebSocket
                            await self._process_dexscreener_data({
                                'type': 'pair',
                                'pair': best_pair
                            })
                            
        except Exception as e:
            logger.error(f"API fetch error for {chain}:{token_address}: {e}")
    
    async def _health_monitor(self):
        """Monitor connection health and reconnect if needed"""
        while self.running:
            try:
                # Check WebSocket connections
                for name, conn in self.connections.items():
                    if conn and conn.closed:
                        logger.warning(f"{name} WebSocket disconnected")
                
                # Log stats
                active_subs = sum(len(subs) for subs in self.subscribers.values())
                cached_prices = len(self.price_cache)
                logger.info(f"Price feeds: {active_subs} subscriptions, {cached_prices} cached prices")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)
    
    def get_latest_price(self, chain: str, token_address: str) -> Optional[Dict]:
        """Get latest cached price for a token"""
        key = f"{chain}:{token_address.lower()}"
        return self.price_cache.get(key)
    
    async def get_price_history(self, chain: str, token_address: str, 
                               interval: str = '5m', limit: int = 100) -> List[Dict]:
        """Get historical price data"""
        # This would fetch from a time-series database or API
        # For now, return empty list
        return []


# Singleton instance
price_feed_manager = PriceFeedManager()