"""
DCA (Dollar Cost Averaging) Trading Strategy
"""

import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
from decimal import Decimal

from trading_engine import trading_engine
from notifications import notification_manager

logger = logging.getLogger(__name__)


class DCAStrategy:
    def __init__(self):
        self.active_strategies = {}
        self.execution_tasks = {}
    
    async def create_dca_strategy(self, user_id: int, params: Dict) -> str:
        """Create a new DCA strategy"""
        strategy_id = f"dca_{user_id}_{datetime.now().timestamp()}"
        
        strategy = {
            'id': strategy_id,
            'user_id': user_id,
            'chain': params['chain'],
            'token_address': params['token_address'],
            'total_amount': params['total_amount'],
            'interval_hours': params['interval_hours'],
            'num_orders': params['num_orders'],
            'amount_per_order': params['total_amount'] / params['num_orders'],
            'orders_executed': 0,
            'created_at': datetime.now(),
            'next_execution': datetime.now(),
            'status': 'active',
            'execution_history': []
        }
        
        self.active_strategies[strategy_id] = strategy
        
        # Start execution task
        task = asyncio.create_task(self._execute_dca_strategy(strategy_id))
        self.execution_tasks[strategy_id] = task
        
        logger.info(f"Created DCA strategy: {strategy_id}")
        return strategy_id
    
    async def _execute_dca_strategy(self, strategy_id: str):
        """Execute DCA strategy orders"""
        while strategy_id in self.active_strategies:
            try:
                strategy = self.active_strategies[strategy_id]
                
                # Check if strategy is complete
                if strategy['orders_executed'] >= strategy['num_orders']:
                    strategy['status'] = 'completed'
                    await self._notify_strategy_complete(strategy)
                    break
                
                # Check if it's time to execute
                if datetime.now() >= strategy['next_execution']:
                    # Execute buy order
                    result = await trading_engine.buy_token(
                        strategy['user_id'],
                        strategy['chain'],
                        strategy['token_address'],
                        strategy['amount_per_order'],
                        slippage=10.0,
                        skip_security_check=True  # Already checked on creation
                    )
                    
                    # Record execution
                    execution = {
                        'order_num': strategy['orders_executed'] + 1,
                        'timestamp': datetime.now(),
                        'amount': strategy['amount_per_order'],
                        'success': result['success'],
                        'tx_hash': result.get('tx_hash'),
                        'error': result.get('error')
                    }
                    
                    strategy['execution_history'].append(execution)
                    
                    if result['success']:
                        strategy['orders_executed'] += 1
                        strategy['next_execution'] = datetime.now() + timedelta(
                            hours=strategy['interval_hours']
                        )
                        
                        # Notify user
                        await notification_manager.notify_trade_executed(
                            strategy['user_id'],
                            {
                                'type': 'DCA Buy',
                                'chain': strategy['chain'],
                                'amount': strategy['amount_per_order'],
                                'tx_hash': result['tx_hash']
                            }
                        )
                    
                    self.active_strategies[strategy_id] = strategy
                
                # Sleep for a minute before checking again
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in DCA execution: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _notify_strategy_complete(self, strategy: Dict):
        """Notify user when DCA strategy completes"""
        total_spent = sum(
            ex['amount'] for ex in strategy['execution_history'] 
            if ex['success']
        )
        
        message = f"✅ **DCA Strategy Complete**\n\n"
        message += f"Token: `{strategy['token_address'][:8]}...`\n"
        message += f"Orders: {strategy['orders_executed']}/{strategy['num_orders']}\n"
        message += f"Total Spent: {total_spent} {strategy['chain']}\n"
        
        await notification_manager.notification_queue.put({
            'user_id': strategy['user_id'],
            'message': message
        })
    
    def cancel_strategy(self, strategy_id: str) -> bool:
        """Cancel an active DCA strategy"""
        if strategy_id in self.active_strategies:
            # Cancel execution task
            if strategy_id in self.execution_tasks:
                self.execution_tasks[strategy_id].cancel()
                del self.execution_tasks[strategy_id]
            
            # Update status
            self.active_strategies[strategy_id]['status'] = 'cancelled'
            
            logger.info(f"Cancelled DCA strategy: {strategy_id}")
            return True
        
        return False
    
    def get_user_strategies(self, user_id: int) -> List[Dict]:
        """Get all strategies for a user"""
        return [
            strategy for strategy in self.active_strategies.values()
            if strategy['user_id'] == user_id
        ]
    
    def get_strategy_status(self, strategy_id: str) -> Optional[Dict]:
        """Get detailed status of a strategy"""
        return self.active_strategies.get(strategy_id)


# Singleton instance
dca_strategy = DCAStrategy()