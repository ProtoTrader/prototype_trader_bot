"""
Arbitrage Bot - Find and execute arbitrage opportunities between DEXs
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import aiohttp

from web3 import Web3
from dex.uniswap_complete import UniswapV2Complete
from trading_engine import trading_engine
from notifications import notification_manager
from utils.retry_manager import with_retry
from config import DEX_ROUTERS, WRAPPED_TOKENS, RPC_ENDPOINTS

logger = logging.getLogger(__name__)


class ArbitrageBot:
    """Multi-DEX arbitrage bot"""
    
    def __init__(self):
        self.active_monitors = {}
        self.monitoring_tasks = {}
        self.arbitrage_history = []
        
        # Initialize Web3 instances
        self.web3_instances = {
            'ETH': Web3(Web3.HTTPProvider(RPC_ENDPOINTS['ETH'][0])),
            'BSC': Web3(Web3.HTTPProvider(RPC_ENDPOINTS['BSC'][0]))
        }
        
        # DEX configurations
        self.dex_configs = {
            'ETH': {
                'uniswap_v2': {
                    'router': DEX_ROUTERS['ETH']['UNISWAP_V2'],
                    'factory': '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',
                    'name': 'Uniswap V2'
                },
                'sushiswap': {
                    'router': DEX_ROUTERS['ETH']['SUSHISWAP'],
                    'factory': '0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac',
                    'name': 'SushiSwap'
                }
            },
            'BSC': {
                'pancakeswap_v2': {
                    'router': DEX_ROUTERS['BSC']['PANCAKESWAP_V2'],
                    'factory': '0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73',
                    'name': 'PancakeSwap V2'
                },
                'biswap': {
                    'router': '0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8',
                    'factory': '0x858E3312ed3A876947EA49d572A7C42DE08af7EE',
                    'name': 'BiSwap'
                }
            }
        }
        
        # Minimum profit thresholds (after gas)
        self.min_profit_thresholds = {
            'ETH': 0.01,  # 0.01 ETH minimum profit
            'BSC': 0.05   # 0.05 BNB minimum profit
        }
    
    async def create_arbitrage_monitor(self, user_id: int, params: Dict) -> str:
        """Create new arbitrage monitor"""
        monitor_id = f"arb_{user_id}_{datetime.now().timestamp()}"
        
        monitor = {
            'id': monitor_id,
            'user_id': user_id,
            'chain': params['chain'],
            'token_addresses': params.get('token_addresses', []),  # Specific tokens or all
            'min_profit_percent': params.get('min_profit_percent', 1.0),  # 1% minimum
            'max_trade_size': params.get('max_trade_size', 1.0),  # Max ETH/BNB per trade
            'check_interval': params.get('check_interval', 5),  # Seconds
            'auto_execute': params.get('auto_execute', False),
            'created_at': datetime.now(),
            'status': 'active',
            'opportunities_found': 0,
            'trades_executed': 0,
            'total_profit': 0.0
        }
        
        self.active_monitors[monitor_id] = monitor
        
        # Start monitoring
        task = asyncio.create_task(self._monitor_arbitrage(monitor_id))
        self.monitoring_tasks[monitor_id] = task
        
        logger.info(f"Created arbitrage monitor: {monitor_id}")
        return monitor_id
    
    async def _monitor_arbitrage(self, monitor_id: str):
        """Monitor for arbitrage opportunities"""
        monitor = self.active_monitors.get(monitor_id)
        if not monitor:
            return
        
        chain = monitor['chain']
        
        logger.info(f"Starting arbitrage monitor on {chain}")
        
        while monitor['status'] == 'active':
            try:
                # Get token list to check
                if monitor['token_addresses']:
                    tokens = monitor['token_addresses']
                else:
                    # Get top tokens by volume
                    tokens = await self._get_top_tokens(chain)
                
                # Check each token for arbitrage
                for token in tokens:
                    opportunity = await self._check_arbitrage_opportunity(
                        chain, token, monitor['max_trade_size']
                    )
                    
                    if opportunity:
                        await self._handle_opportunity(monitor, opportunity)
                
                await asyncio.sleep(monitor['check_interval'])
                
            except Exception as e:
                logger.error(f"Arbitrage monitor error: {e}")
                await asyncio.sleep(30)
    
    async def _check_arbitrage_opportunity(self, chain: str, token_address: str, 
                                         max_trade_size: float) -> Optional[Dict]:
        """Check for arbitrage opportunity between DEXs"""
        try:
            dexs = self.dex_configs.get(chain, {})
            if len(dexs) < 2:
                return None
            
            # Get prices from all DEXs
            prices = {}
            for dex_name, dex_config in dexs.items():
                price = await self._get_token_price_on_dex(
                    chain, token_address, dex_config, max_trade_size
                )
                if price:
                    prices[dex_name] = price
            
            if len(prices) < 2:
                return None
            
            # Find best arbitrage path
            best_opportunity = None
            max_profit = 0
            
            for buy_dex, buy_price in prices.items():
                for sell_dex, sell_price in prices.items():
                    if buy_dex == sell_dex:
                        continue
                    
                    # Calculate potential profit
                    if buy_price['price'] > 0 and sell_price['price'] > buy_price['price']:
                        # Buy low, sell high
                        profit_ratio = (sell_price['price'] - buy_price['price']) / buy_price['price']
                        
                        # Calculate actual amounts considering slippage
                        buy_amount = min(max_trade_size, buy_price['max_input'])
                        expected_tokens = buy_amount / buy_price['price_with_slippage']
                        sell_output = expected_tokens * sell_price['price_with_slippage']
                        
                        # Estimate gas costs
                        gas_cost = await self._estimate_gas_cost(chain)
                        
                        net_profit = sell_output - buy_amount - gas_cost
                        
                        if net_profit > max_profit and net_profit > self.min_profit_thresholds.get(chain, 0):
                            max_profit = net_profit
                            best_opportunity = {
                                'token_address': token_address,
                                'buy_dex': buy_dex,
                                'sell_dex': sell_dex,
                                'buy_price': buy_price['price'],
                                'sell_price': sell_price['price'],
                                'buy_amount': buy_amount,
                                'expected_tokens': expected_tokens,
                                'expected_output': sell_output,
                                'gas_cost': gas_cost,
                                'net_profit': net_profit,
                                'profit_percent': profit_ratio * 100,
                                'timestamp': datetime.now()
                            }
            
            return best_opportunity
            
        except Exception as e:
            logger.error(f"Error checking arbitrage: {e}")
            return None
    
    async def _get_token_price_on_dex(self, chain: str, token_address: str,
                                    dex_config: Dict, amount: float) -> Optional[Dict]:
        """Get token price on specific DEX"""
        try:
            w3 = self.web3_instances.get(chain)
            if not w3:
                return None
            
            # Initialize DEX trader
            trader = UniswapV2Complete(
                w3,
                dex_config['router'],
                dex_config['factory'],
                WRAPPED_TOKENS[chain]
            )
            
            # Get price for buying with ETH/BNB
            price_info = await trader.get_token_price(token_address, amount)
            
            if price_info:
                return {
                    'price': price_info['price_eth'],
                    'price_with_slippage': price_info['price_eth'] * 1.01,  # 1% slippage
                    'liquidity': price_info['liquidity_eth'],
                    'max_input': min(amount, price_info['liquidity_eth'] * 0.1),  # Max 10% of pool
                    'dex_name': dex_config['name']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting price from {dex_config['name']}: {e}")
            return None
    
    async def _estimate_gas_cost(self, chain: str) -> float:
        """Estimate gas cost for arbitrage (2 swaps)"""
        try:
            w3 = self.web3_instances.get(chain)
            if not w3:
                return 0.1  # Default high estimate
            
            gas_price = w3.eth.gas_price
            
            # Estimate gas for 2 swaps + approval
            gas_estimate = 300000  # Approximate for 2 swaps
            
            gas_cost_wei = gas_price * gas_estimate
            gas_cost_native = w3.from_wei(gas_cost_wei, 'ether')
            
            return float(gas_cost_native)
            
        except Exception as e:
            logger.error(f"Error estimating gas: {e}")
            return 0.1  # Default
    
    async def _handle_opportunity(self, monitor: Dict, opportunity: Dict):
        """Handle found arbitrage opportunity"""
        try:
            monitor['opportunities_found'] += 1
            
            # Log opportunity
            logger.info(
                f"Arbitrage opportunity found: {opportunity['profit_percent']:.2f}% profit "
                f"({opportunity['net_profit']:.4f} {monitor['chain']})"
            )
            
            # Check if meets minimum profit requirement
            if opportunity['profit_percent'] < monitor['min_profit_percent']:
                return
            
            # Notify user
            await self._notify_opportunity(monitor['user_id'], monitor['chain'], opportunity)
            
            # Execute if auto-execute enabled
            if monitor['auto_execute']:
                success = await self._execute_arbitrage(monitor, opportunity)
                
                if success:
                    monitor['trades_executed'] += 1
                    monitor['total_profit'] += opportunity['net_profit']
                    
                    # Record in history
                    self.arbitrage_history.append({
                        'monitor_id': monitor['id'],
                        'opportunity': opportunity,
                        'executed': True,
                        'timestamp': datetime.now()
                    })
            else:
                # Record opportunity without execution
                self.arbitrage_history.append({
                    'monitor_id': monitor['id'],
                    'opportunity': opportunity,
                    'executed': False,
                    'timestamp': datetime.now()
                })
                
        except Exception as e:
            logger.error(f"Error handling opportunity: {e}")
    
    async def _notify_opportunity(self, user_id: int, chain: str, opportunity: Dict):
        """Notify user of arbitrage opportunity"""
        message = f"💰 **Arbitrage Opportunity**\n\n"
        message += f"Chain: **{chain}**\n"
        message += f"Token: `{opportunity['token_address'][:8]}...`\n"
        message += f"Buy on: **{opportunity['buy_dex']}**\n"
        message += f"Sell on: **{opportunity['sell_dex']}**\n"
        message += f"Profit: **{opportunity['profit_percent']:.2f}%** "
        message += f"({opportunity['net_profit']:.4f} {chain})\n"
        message += f"Amount: {opportunity['buy_amount']:.3f} {chain}"
        
        await notification_manager.notification_queue.put({
            'user_id': user_id,
            'message': message
        })
    
    async def _execute_arbitrage(self, monitor: Dict, opportunity: Dict) -> bool:
        """Execute arbitrage trade"""
        try:
            user_id = monitor['user_id']
            chain = monitor['chain']
            
            # Step 1: Buy on first DEX
            buy_result = await trading_engine.buy_token(
                user_id=user_id,
                chain=chain,
                token_address=opportunity['token_address'],
                amount=opportunity['buy_amount'],
                slippage=2.0,  # Low slippage for arbitrage
                skip_security_check=True
            )
            
            if not buy_result['success']:
                logger.error(f"Arbitrage buy failed: {buy_result.get('error')}")
                return False
            
            # Step 2: Wait for confirmation
            # In production, would wait for block confirmation
            await asyncio.sleep(2)
            
            # Step 3: Sell on second DEX
            # Calculate token amount to sell (100% of received tokens)
            sell_result = await trading_engine.sell_token(
                user_id=user_id,
                chain=chain,
                token_address=opportunity['token_address'],
                amount=100,  # 100% of holdings
                slippage=2.0
            )
            
            if not sell_result['success']:
                logger.error(f"Arbitrage sell failed: {sell_result.get('error')}")
                # Still have tokens, user can manually sell
                return False
            
            # Success notification
            await notification_manager.notify_trade_executed(
                user_id,
                {
                    'type': 'ARBITRAGE',
                    'chain': chain,
                    'amount': opportunity['net_profit'],
                    'tx_hash': sell_result['tx_hash']
                }
            )
            
            logger.info(f"Arbitrage executed successfully: {opportunity['net_profit']:.4f} {chain} profit")
            return True
            
        except Exception as e:
            logger.error(f"Arbitrage execution failed: {e}")
            return False
    
    async def _get_top_tokens(self, chain: str, limit: int = 20) -> List[str]:
        """Get top tokens by volume to monitor"""
        # This would fetch from DexScreener or similar API
        # For now, return popular tokens
        
        if chain == 'ETH':
            return [
                '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',  # USDC
                '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
                '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # DAI
                '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',  # WBTC
                '0x514910771AF9Ca656af840dff83E8264EcF986CA',  # LINK
            ]
        elif chain == 'BSC':
            return [
                '0x55d398326f99059fF775485246999027B3197955',  # USDT
                '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',  # BUSD
                '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',  # USDC
                '0x2170Ed0880ac9A755fd29B2688956BD959F933F8',  # ETH
            ]
        
        return []
    
    def cancel_monitor(self, monitor_id: str) -> bool:
        """Cancel arbitrage monitor"""
        if monitor_id in self.active_monitors:
            self.active_monitors[monitor_id]['status'] = 'cancelled'
            
            # Cancel task
            if monitor_id in self.monitoring_tasks:
                self.monitoring_tasks[monitor_id].cancel()
                del self.monitoring_tasks[monitor_id]
            
            logger.info(f"Cancelled arbitrage monitor: {monitor_id}")
            return True
        
        return False
    
    def get_user_monitors(self, user_id: int) -> List[Dict]:
        """Get all monitors for a user"""
        return [
            monitor for monitor in self.active_monitors.values()
            if monitor['user_id'] == user_id
        ]
    
    def get_arbitrage_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get arbitrage history for user"""
        user_history = [
            h for h in self.arbitrage_history
            if self.active_monitors.get(h['monitor_id'], {}).get('user_id') == user_id
        ]
        
        # Sort by timestamp descending
        user_history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return user_history[:limit]


# Singleton instance
arbitrage_bot = ArbitrageBot()