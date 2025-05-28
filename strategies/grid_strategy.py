"""
Grid Trading Strategy
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging
from decimal import Decimal

from trading_engine import trading_engine
from notifications import notification_manager

logger = logging.getLogger(__name__)


class GridStrategy:
    def __init__(self):
        self.active_grids = {}
        self.monitoring_tasks = {}
    
    async def create_grid_strategy(self, user_id: int, params: Dict) -> str:
        """Create a new grid trading strategy"""
        strategy_id = f"grid_{user_id}_{datetime.now().timestamp()}"
        
        # Calculate grid levels
        price_range = params['upper_price'] - params['lower_price']
        grid_size = price_range / params['num_grids']
        
        grid_levels = []
        for i in range(params['num_grids'] + 1):
            price = params['lower_price'] + (i * grid_size)
            grid_levels.append({
                'price': price,
                'buy_order': None,
                'sell_order': None,
                'filled': False
            })
        
        strategy = {
            'id': strategy_id,
            'user_id': user_id,
            'chain': params['chain'],
            'token_address': params['token_address'],
            'total_investment': params['total_investment'],
            'amount_per_grid': params['total_investment'] / params['num_grids'],
            'upper_price': params['upper_price'],
            'lower_price': params['lower_price'],
            'num_grids': params['num_grids'],
            'grid_levels': grid_levels,
            'created_at': datetime.now(),
            'status': 'active',
            'total_profit': 0,
            'trades_executed': 0
        }
        
        self.active_grids[strategy_id] = strategy
        
        # Start monitoring task
        task = asyncio.create_task(self._monitor_grid_strategy(strategy_id))
        self.monitoring_tasks[strategy_id] = task
        
        # Place initial orders
        await self._place_initial_orders(strategy_id)
        
        logger.info(f"Created grid strategy: {strategy_id}")
        return strategy_id
    
    async def _place_initial_orders(self, strategy_id: str):
        """Place initial grid orders"""
        strategy = self.active_grids.get(strategy_id)
        if not strategy:
            return
        
        # Get current price
        current_price = await self._get_current_price(
            strategy['chain'], 
            strategy['token_address']
        )
        
        if not current_price:
            logger.error(f"Failed to get current price for grid {strategy_id}")
            return
        
        # Place buy orders below current price
        for i, level in enumerate(strategy['grid_levels']):
            if level['price'] < current_price * 0.99:  # 1% buffer
                # Place buy order
                logger.info(f"Placing buy order at {level['price']}")
                # In production, this would place limit orders on DEX
                level['buy_order'] = {
                    'price': level['price'],
                    'amount': strategy['amount_per_grid'] / level['price'],
                    'status': 'pending'
                }
        
        # Place sell orders above current price (if holding tokens)
        # This would check user's token balance first
        
        self.active_grids[strategy_id] = strategy
    
    async def _monitor_grid_strategy(self, strategy_id: str):
        """Monitor grid strategy and execute trades"""
        while strategy_id in self.active_grids:
            try:
                strategy = self.active_grids[strategy_id]
                
                if strategy['status'] != 'active':
                    break
                
                # Get current price
                current_price = await self._get_current_price(
                    strategy['chain'],
                    strategy['token_address']
                )
                
                if not current_price:
                    await asyncio.sleep(30)
                    continue
                
                # Check each grid level
                for i, level in enumerate(strategy['grid_levels']):
                    # Check if buy order should be filled
                    if (level['buy_order'] and 
                        level['buy_order']['status'] == 'pending' and
                        current_price <= level['price']):
                        
                        # Execute buy
                        result = await trading_engine.buy_token(
                            strategy['user_id'],
                            strategy['chain'],
                            strategy['token_address'],
                            strategy['amount_per_grid'],
                            slippage=5.0,
                            skip_security_check=True
                        )
                        
                        if result['success']:
                            level['buy_order']['status'] = 'filled'
                            level['filled'] = True
                            strategy['trades_executed'] += 1
                            
                            # Place sell order at next level up
                            if i < len(strategy['grid_levels']) - 1:
                                next_level = strategy['grid_levels'][i + 1]
                                next_level['sell_order'] = {
                                    'price': next_level['price'],
                                    'amount': level['buy_order']['amount'],
                                    'status': 'pending'
                                }
                            
                            # Notify user
                            await self._notify_grid_filled(strategy, 'buy', level['price'])
                    
                    # Check if sell order should be filled
                    elif (level['sell_order'] and 
                          level['sell_order']['status'] == 'pending' and
                          current_price >= level['price']):
                        
                        # Execute sell
                        result = await trading_engine.sell_token(
                            strategy['user_id'],
                            strategy['chain'],
                            strategy['token_address'],
                            level['sell_order']['amount'],
                            slippage=5.0
                        )
                        
                        if result['success']:
                            level['sell_order']['status'] = 'filled'
                            strategy['trades_executed'] += 1
                            
                            # Calculate profit
                            buy_price = strategy['grid_levels'][i-1]['price']
                            profit = (level['price'] - buy_price) * level['sell_order']['amount']
                            strategy['total_profit'] += profit
                            
                            # Place buy order at previous level
                            if i > 0:
                                prev_level = strategy['grid_levels'][i - 1]
                                prev_level['buy_order'] = {
                                    'price': prev_level['price'],
                                    'amount': strategy['amount_per_grid'] / prev_level['price'],
                                    'status': 'pending'
                                }
                                prev_level['filled'] = False
                            
                            # Notify user
                            await self._notify_grid_filled(strategy, 'sell', level['price'])
                
                self.active_grids[strategy_id] = strategy
                
                # Sleep before next check
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in grid monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _get_current_price(self, chain: str, token_address: str) -> Optional[float]:
        """Get current token price"""
        # This would get real price from DEX
        # For now return mock price
        import random
        base_price = 0.001
        variation = random.uniform(-0.00005, 0.00005)
        return base_price + variation
    
    async def _notify_grid_filled(self, strategy: Dict, order_type: str, price: float):
        """Notify user when grid order is filled"""
        emoji = "🟢" if order_type == 'buy' else "🔴"
        
        message = f"{emoji} **Grid Order Filled**\n\n"
        message += f"Type: **{order_type.upper()}**\n"
        message += f"Price: **${price:.6f}**\n"
        message += f"Grid: {strategy['trades_executed']} trades\n"
        
        if strategy['total_profit'] > 0:
            message += f"Total Profit: **+${strategy['total_profit']:.2f}**\n"
        
        await notification_manager.notification_queue.put({
            'user_id': strategy['user_id'],
            'message': message
        })
    
    def cancel_strategy(self, strategy_id: str) -> bool:
        """Cancel a grid strategy"""
        if strategy_id in self.active_grids:
            # Cancel monitoring task
            if strategy_id in self.monitoring_tasks:
                self.monitoring_tasks[strategy_id].cancel()
                del self.monitoring_tasks[strategy_id]
            
            # Update status
            self.active_grids[strategy_id]['status'] = 'cancelled'
            
            # In production, would also cancel all pending orders
            
            logger.info(f"Cancelled grid strategy: {strategy_id}")
            return True
        
        return False
    
    def get_user_strategies(self, user_id: int) -> List[Dict]:
        """Get all grid strategies for a user"""
        return [
            strategy for strategy in self.active_grids.values()
            if strategy['user_id'] == user_id
        ]


# Singleton instance
grid_strategy = GridStrategy()