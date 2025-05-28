"""
Background Tasks Manager - Handles periodic tasks and monitoring
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from cache.redis_cache import RedisCache
from queues.task_queue import TaskQueue, NotificationQueue, AnalyticsQueue, TaskPriority
from price_feeds.websocket_manager import WebSocketManager
from monitor import PriceMonitor
from strategies.arbitrage_bot import ArbitrageBot

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """Manages all background tasks and periodic jobs"""
    
    def __init__(self):
        self.cache = RedisCache()
        self.notification_queue = NotificationQueue(self.cache)
        self.analytics_queue = AnalyticsQueue(self.cache)
        self.tasks = {}
        self.running = False
        
    async def start(self):
        """Start all background tasks"""
        self.running = True
        
        # Start queues
        await self.notification_queue.start(num_workers=2)
        await self.analytics_queue.start(num_workers=2)
        
        # Start periodic tasks
        self.tasks['price_updater'] = asyncio.create_task(self._update_prices())
        self.tasks['cache_cleaner'] = asyncio.create_task(self._clean_cache())
        self.tasks['analytics_processor'] = asyncio.create_task(self._process_analytics())
        self.tasks['arbitrage_scanner'] = asyncio.create_task(self._scan_arbitrage())
        self.tasks['position_monitor'] = asyncio.create_task(self._monitor_positions())
        
        logger.info("Background task manager started")
        
    async def stop(self):
        """Stop all background tasks"""
        self.running = False
        
        # Stop queues
        await self.notification_queue.stop()
        await self.analytics_queue.stop()
        
        # Cancel all tasks
        for task_name, task in self.tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        logger.info("Background task manager stopped")
        
    async def _update_prices(self):
        """Periodically update token prices in cache"""
        while self.running:
            try:
                # Get list of tokens to update from active trades
                tokens_to_update = self._get_active_tokens()
                
                for chain, token in tokens_to_update:
                    try:
                        # Skip if recently updated
                        if self.cache.get_price(chain, token):
                            continue
                            
                        # Fetch and cache price
                        from trading_engine import trading_engine
                        price = await trading_engine._fetch_price_from_dex(chain, token)
                        if price:
                            self.cache.set_price(chain, token, price)
                            
                    except Exception as e:
                        logger.error(f"Error updating price for {chain}:{token}: {e}")
                        
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Price updater error: {e}")
                await asyncio.sleep(30)
                
    async def _clean_cache(self):
        """Periodically clean expired cache entries"""
        while self.running:
            try:
                # Clean old price data
                self.cache.clear_pattern("price:*")
                
                # Clean old transaction data older than 7 days
                cutoff_time = datetime.now() - timedelta(days=7)
                # Implementation would check transaction timestamps
                
                await asyncio.sleep(3600)  # Clean every hour
                
            except Exception as e:
                logger.error(f"Cache cleaner error: {e}")
                await asyncio.sleep(3600)
                
    async def _process_analytics(self):
        """Process analytics data periodically"""
        while self.running:
            try:
                # Calculate daily statistics
                await self.analytics_queue.enqueue(
                    'update_statistics',
                    {'type': 'daily', 'date': datetime.now().date().isoformat()},
                    priority=TaskPriority.LOW
                )
                
                # Process user PnL
                active_users = self._get_active_users()
                for user_id in active_users:
                    await self.analytics_queue.enqueue(
                        'calculate_pnl',
                        {'user_id': user_id, 'period': 'daily'},
                        priority=TaskPriority.LOW
                    )
                    
                await asyncio.sleep(3600)  # Process every hour
                
            except Exception as e:
                logger.error(f"Analytics processor error: {e}")
                await asyncio.sleep(3600)
                
    async def _scan_arbitrage(self):
        """Scan for arbitrage opportunities"""
        while self.running:
            try:
                # Get list of tokens with sufficient liquidity
                popular_tokens = self._get_popular_tokens()
                
                for chain in ['ETH', 'BSC']:
                    for token in popular_tokens.get(chain, []):
                        # Check if recently scanned
                        scan_key = f"arb_scan:{chain}:{token}"
                        if self.cache.exists(scan_key):
                            continue
                            
                        # Mark as scanned
                        self.cache.set(scan_key, True, expire=300)  # 5 minutes
                        
                        # Queue arbitrage check
                        try:
                            arb_bot = ArbitrageBot()
                            opportunities = await arb_bot.find_arbitrage_opportunity(
                                token, chain
                            )
                            
                            if opportunities:
                                # Notify users subscribed to arbitrage alerts
                                await self._notify_arbitrage(opportunities)
                                
                        except Exception as e:
                            logger.error(f"Arbitrage scan error: {e}")
                            
                await asyncio.sleep(30)  # Scan every 30 seconds
                
            except Exception as e:
                logger.error(f"Arbitrage scanner error: {e}")
                await asyncio.sleep(60)
                
    async def _monitor_positions(self):
        """Monitor user positions for stop loss and take profit"""
        while self.running:
            try:
                # Get all active positions with SL/TP
                from trading_engine import trading_engine
                
                for trade_id, monitor in trading_engine.price_monitors.items():
                    if not monitor.get('monitoring', False):
                        continue
                        
                    trade = trading_engine.active_trades.get(trade_id)
                    if not trade:
                        continue
                        
                    # Check price and trigger if needed
                    current_price = self.cache.get_price(trade['chain'], trade['token_address'])
                    if not current_price:
                        continue
                        
                    initial_price = monitor['initial_price']
                    price_change = ((current_price - initial_price) / initial_price) * 100
                    
                    # Check stop loss
                    if 'stop_loss' in trade and price_change <= -trade['stop_loss']:
                        await self._trigger_stop_loss(trade_id, trade)
                        
                    # Check take profit
                    elif 'take_profit' in trade and price_change >= trade['take_profit']:
                        await self._trigger_take_profit(trade_id, trade)
                        
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Position monitor error: {e}")
                await asyncio.sleep(10)
                
    def _get_active_tokens(self) -> List[tuple]:
        """Get list of tokens from active trades"""
        from trading_engine import trading_engine
        tokens = set()
        
        for trade in trading_engine.active_trades.values():
            tokens.add((trade['chain'], trade['token_address']))
            
        return list(tokens)
        
    def _get_active_users(self) -> List[int]:
        """Get list of active users"""
        from user_data import user_data
        # Return users who have traded in the last 24 hours
        active_users = []
        cutoff_time = datetime.now() - timedelta(days=1)
        
        for user_id, data in user_data.items():
            if 'last_trade' in data and data['last_trade'] > cutoff_time:
                active_users.append(user_id)
                
        return active_users
        
    def _get_popular_tokens(self) -> Dict[str, List[str]]:
        """Get popular tokens by chain"""
        # This would be populated from actual trading data
        return {
            'ETH': [
                '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',  # USDC
                '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
                '0x514910771AF9Ca656af840dff83E8264EcF986CA',  # LINK
            ],
            'BSC': [
                '0x55d398326f99059fF775485246999027B3197955',  # USDT
                '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',  # BUSD
            ]
        }
        
    async def _notify_arbitrage(self, opportunities: List[Dict]):
        """Notify users about arbitrage opportunities"""
        from user_data import user_data
        
        for user_id, data in user_data.items():
            if data.get('notifications', {}).get('arbitrage', False):
                await self.notification_queue.enqueue(
                    'send_alert',
                    {
                        'user_id': user_id,
                        'type': 'arbitrage',
                        'opportunities': opportunities
                    },
                    priority=TaskPriority.HIGH
                )
                
    async def _trigger_stop_loss(self, trade_id: str, trade: Dict):
        """Trigger stop loss for a trade"""
        logger.info(f"Triggering stop loss for trade {trade_id}")
        
        # Queue high priority sell
        from trading_engine import trading_engine
        await trading_engine.sell_token(
            trade['user_id'],
            trade['chain'],
            trade['token_address'],
            trade['amount'],
            slippage=15.0,  # Higher slippage for emergency sells
            use_queue=False  # Execute immediately
        )
        
        # Update monitoring status
        trading_engine.price_monitors[trade_id]['monitoring'] = False
        
        # Send notification
        await self.notification_queue.enqueue(
            'send_telegram',
            {
                'user_id': trade['user_id'],
                'text': f"⚠️ Stop loss triggered for {trade['token_address']}\\n"
                       f"Sold {trade['amount']} tokens"
            },
            priority=TaskPriority.URGENT
        )
        
    async def _trigger_take_profit(self, trade_id: str, trade: Dict):
        """Trigger take profit for a trade"""
        logger.info(f"Triggering take profit for trade {trade_id}")
        
        # Calculate sell amount
        sell_amount = trade['amount'] * trade.get('take_profit_amount', 50) / 100
        
        # Queue sell
        from trading_engine import trading_engine
        await trading_engine.sell_token(
            trade['user_id'],
            trade['chain'],
            trade['token_address'],
            sell_amount,
            slippage=5.0,
            use_queue=False  # Execute immediately
        )
        
        # Update monitoring status
        trading_engine.price_monitors[trade_id]['monitoring'] = False
        
        # Send notification
        await self.notification_queue.enqueue(
            'send_telegram',
            {
                'user_id': trade['user_id'],
                'text': f"🎯 Take profit triggered for {trade['token_address']}\\n"
                       f"Sold {sell_amount} tokens"
            },
            priority=TaskPriority.HIGH
        )

# Global instance
background_manager = BackgroundTaskManager()