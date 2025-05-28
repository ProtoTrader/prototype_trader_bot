"""
Trading Engine - Handles trading operations, orders, and price monitoring
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import aiohttp
from web3 import Web3
from solana.rpc.async_api import AsyncClient
from wallet_manager import wallet_manager
from config import FEE_PERCENTAGE, FEE_WALLETS, DEX_ROUTERS, WRAPPED_TOKENS, RPC_ENDPOINTS
from dex.uniswap import UniswapTrader
from dex.raydium import RaydiumTrader
from security.honeypot_scanner import scan_token_security
from cache.redis_cache import RedisCache, cached
from queues.task_queue import TradingQueue, TaskPriority

logger = logging.getLogger(__name__)


class TradingEngine:
    """Manages trading operations across different chains"""
    
    def __init__(self):
        self.active_trades = {}
        self.price_monitors = {}
        self.cache = RedisCache()
        self.trading_queue = TradingQueue(self.cache)
        self.web3_clients = {
            'ETH': Web3(Web3.HTTPProvider('https://eth.llamarpc.com')),
            'BSC': Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
        }
        self.solana_client = AsyncClient("https://api.mainnet-beta.solana.com")
        
    async def start_queue_processing(self):
        """Start the trading queue workers"""
        await self.trading_queue.start(num_workers=5)
        
    async def buy_token(self, user_id: int, chain: str, token_address: str, 
                       amount: float, slippage: float = 10.0, gas_delta: float = 0.001, 
                       skip_security_check: bool = False, use_queue: bool = True) -> Dict:
        """Execute a buy order with fee deduction and security checks"""
        # Queue the task if requested
        if use_queue:
            task_id = await self.trading_queue.enqueue(
                'buy_token',
                {
                    'wallet_address': user_id,  # Will be resolved in handler
                    'chain': chain,
                    'token_address': token_address,
                    'amount': amount,
                    'slippage': slippage,
                    'user_id': user_id
                },
                priority=TaskPriority.HIGH
            )
            return {'success': True, 'task_id': task_id, 'queued': True}
            
        try:
            # Security check first (unless explicitly skipped)
            if not skip_security_check and chain in ['ETH', 'BSC']:
                security_result = await scan_token_security(chain, token_address)
                if security_result['is_honeypot']:
                    return {
                        'success': False, 
                        'error': f"Token failed security check: {', '.join(security_result['warnings'])}",
                        'security_result': security_result
                    }
                elif security_result['risk_level'] in ['HIGH', 'CRITICAL']:
                    logger.warning(f"High risk token detected: {token_address}")
            
            # Get user's wallet
            wallet = self._get_user_wallet(user_id, chain)
            if not wallet:
                return {'success': False, 'error': 'No wallet connected'}
            
            # Calculate fee amount (1% of trade)
            fee_amount = amount * FEE_PERCENTAGE
            actual_trade_amount = amount - fee_amount
            
            # Send fee to project wallet first
            fee_tx = await self._send_fee(wallet, chain, fee_amount)
            if not fee_tx:
                return {'success': False, 'error': 'Failed to process fee transaction'}
            
            # Prepare transaction based on chain
            if chain == 'ETH':
                tx_hash = await self._buy_eth_token(wallet, token_address, actual_trade_amount, slippage, gas_delta)
            elif chain == 'SOL':
                tx_hash = await self._buy_sol_token(wallet, token_address, actual_trade_amount, slippage)
            elif chain == 'TRX':
                tx_hash = await self._buy_trx_token(wallet, token_address, actual_trade_amount, slippage)
            else:
                return {'success': False, 'error': f'Unsupported chain: {chain}'}
            
            # Record trade
            trade_id = self._generate_trade_id()
            self.active_trades[trade_id] = {
                'user_id': user_id,
                'chain': chain,
                'token_address': token_address,
                'type': 'buy',
                'amount': amount,
                'tx_hash': tx_hash,
                'timestamp': datetime.now(),
                'status': 'pending'
            }
            
            return {
                'success': True,
                'trade_id': trade_id,
                'tx_hash': tx_hash
            }
            
        except Exception as e:
            logger.error(f"Buy order failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def sell_token(self, user_id: int, chain: str, token_address: str,
                        amount: float, slippage: float = 10.0, gas_delta: float = 0.001) -> Dict:
        """Execute a sell order"""
        try:
            # Get user's wallet
            wallet = self._get_user_wallet(user_id, chain)
            if not wallet:
                return {'success': False, 'error': 'No wallet connected'}
            
            # Prepare transaction based on chain
            if chain == 'ETH':
                tx_hash = await self._sell_eth_token(wallet, token_address, amount, slippage, gas_delta)
            elif chain == 'SOL':
                tx_hash = await self._sell_sol_token(wallet, token_address, amount, slippage)
            elif chain == 'TRX':
                tx_hash = await self._sell_trx_token(wallet, token_address, amount, slippage)
            else:
                return {'success': False, 'error': f'Unsupported chain: {chain}'}
            
            # Record trade
            trade_id = self._generate_trade_id()
            self.active_trades[trade_id] = {
                'user_id': user_id,
                'chain': chain,
                'token_address': token_address,
                'type': 'sell',
                'amount': amount,
                'tx_hash': tx_hash,
                'timestamp': datetime.now(),
                'status': 'pending'
            }
            
            return {
                'success': True,
                'trade_id': trade_id,
                'tx_hash': tx_hash
            }
            
        except Exception as e:
            logger.error(f"Sell order failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def set_stop_loss(self, trade_id: str, stop_loss_percent: float) -> bool:
        """Set stop loss for an active trade"""
        if trade_id not in self.active_trades:
            return False
        
        trade = self.active_trades[trade_id]
        trade['stop_loss'] = stop_loss_percent
        
        # Start monitoring if not already
        if trade_id not in self.price_monitors:
            asyncio.create_task(self._monitor_trade(trade_id))
        
        return True
    
    async def set_take_profit(self, trade_id: str, take_profit_percent: float) -> bool:
        """Set take profit for an active trade"""
        if trade_id not in self.active_trades:
            return False
        
        trade = self.active_trades[trade_id]
        trade['take_profit'] = take_profit_percent
        
        # Start monitoring if not already
        if trade_id not in self.price_monitors:
            asyncio.create_task(self._monitor_trade(trade_id))
        
        return True
    
    async def _monitor_trade(self, trade_id: str):
        """Monitor trade for stop loss and take profit"""
        trade = self.active_trades.get(trade_id)
        if not trade:
            return
        
        initial_price = await self._get_token_price(trade['chain'], trade['token_address'])
        if not initial_price:
            return
        
        self.price_monitors[trade_id] = {
            'initial_price': initial_price,
            'monitoring': True
        }
        
        while self.price_monitors[trade_id]['monitoring']:
            try:
                current_price = await self._get_token_price(trade['chain'], trade['token_address'])
                if not current_price:
                    await asyncio.sleep(5)
                    continue
                
                price_change = ((current_price - initial_price) / initial_price) * 100
                
                # Check stop loss
                if 'stop_loss' in trade and price_change <= -trade['stop_loss']:
                    logger.info(f"Stop loss triggered for trade {trade_id}")
                    await self.sell_token(
                        trade['user_id'],
                        trade['chain'],
                        trade['token_address'],
                        trade['amount'],
                        slippage=15.0  # Higher slippage for emergency sells
                    )
                    self.price_monitors[trade_id]['monitoring'] = False
                
                # Check take profit
                elif 'take_profit' in trade and price_change >= trade['take_profit']:
                    logger.info(f"Take profit triggered for trade {trade_id}")
                    await self.sell_token(
                        trade['user_id'],
                        trade['chain'],
                        trade['token_address'],
                        trade['amount'] * trade.get('take_profit_amount', 50) / 100
                    )
                    self.price_monitors[trade_id]['monitoring'] = False
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring trade {trade_id}: {e}")
                await asyncio.sleep(10)
    
    @cached(expire=30)  # Cache for 30 seconds
    async def _get_token_price(self, chain: str, token_address: str) -> Optional[float]:
        """Get current token price with caching"""
        # Check cache first
        cached_price = self.cache.get_price(chain, token_address)
        if cached_price is not None:
            return cached_price
            
        # Fetch from DEX if not cached
        price = await self._fetch_price_from_dex(chain, token_address)
        if price:
            self.cache.set_price(chain, token_address, price, expire=30)
        return price
        
    async def _fetch_price_from_dex(self, chain: str, token_address: str) -> Optional[float]:
        """Fetch price from DEX"""
        # This is still a placeholder - would integrate with actual DEX APIs
        return 1.0
    
    def _get_user_wallet(self, user_id: int, chain: str) -> Optional[Dict]:
        """Get user's wallet for the specified chain"""
        from user_data import user_data
        
        if user_id not in user_data:
            return None
        
        # Check for connected wallet first, then generated wallet
        if 'connected_wallets' in user_data[user_id] and chain in user_data[user_id]['connected_wallets']:
            wallet_info = user_data[user_id]['connected_wallets'][chain]
        elif 'generated_wallets' in user_data[user_id] and chain in user_data[user_id]['generated_wallets']:
            wallet_info = user_data[user_id]['generated_wallets'][chain]
        else:
            return None
        
        # Decrypt private key
        private_key = wallet_manager.decrypt_private_key(wallet_info['private_key_encrypted'])
        
        return {
            'address': wallet_info['address'],
            'private_key': private_key,
            'chain': chain
        }
    
    def _generate_trade_id(self) -> str:
        """Generate unique trade ID"""
        import uuid
        return str(uuid.uuid4())
    
    async def _send_fee(self, wallet: Dict, chain: str, fee_amount: float) -> Optional[str]:
        """Send fee to project wallet with caching"""
        try:
            fee_wallet = FEE_WALLETS.get(chain)
            if not fee_wallet:
                logger.error(f"No fee wallet configured for {chain}")
                return None
            
            # Check if we recently sent a fee (rate limiting)
            rate_key = f"fee_rate:{wallet['address']}:{chain}"
            if not self.cache.check_rate_limit(rate_key, 10):  # Max 10 fees per minute
                logger.warning("Fee rate limit exceeded")
                return None
                
            tx_hash = None
            if chain == 'ETH':
                tx_hash = await self._send_eth_fee(wallet, fee_wallet, fee_amount)
            elif chain == 'SOL':
                tx_hash = await self._send_sol_fee(wallet, fee_wallet, fee_amount)
            elif chain == 'TRX':
                tx_hash = await self._send_trx_fee(wallet, fee_wallet, fee_amount)
                
            if tx_hash:
                self.cache.increment_rate_limit(rate_key)
                # Cache transaction for quick lookup
                self.cache.cache_transaction(tx_hash, {
                    'type': 'fee',
                    'chain': chain,
                    'amount': fee_amount,
                    'from': wallet['address'],
                    'to': fee_wallet
                })
                
            return tx_hash
        except Exception as e:
            logger.error(f"Failed to send fee: {e}")
            return None
    
    async def _buy_eth_token(self, wallet: Dict, token_address: str, amount: float, 
                            slippage: float, gas_delta: float) -> str:
        """Execute buy on Ethereum/BSC using Uniswap with gas price caching"""
        try:
            # Get cached gas price or fetch new one
            gas_price = self.cache.get_gas_price('ETH')
            if not gas_price:
                gas_price = await self._fetch_gas_price('ETH')
                self.cache.set_gas_price('ETH', gas_price, expire=30)
                
            # Initialize Uniswap trader
            web3_client = self.web3_clients['ETH']
            uniswap = UniswapTrader(
                web3_client,
                DEX_ROUTERS['ETH']['UNISWAP_V2'],
                WRAPPED_TOKENS['ETH']
            )
            
            # Execute buy
            result = await uniswap.buy_token(
                wallet['address'],
                wallet['private_key'],
                token_address,
                amount,
                slippage,
                gas_delta * 1000  # Convert to gwei
            )
            
            if result['success']:
                # Cache successful transaction
                self.cache.cache_transaction(result['tx_hash'], {
                    'type': 'buy',
                    'chain': 'ETH',
                    'token': token_address,
                    'amount': amount,
                    'wallet': wallet['address']
                })
                return result['tx_hash']
            else:
                raise Exception(result['error'])
                
        except Exception as e:
            logger.error(f"ETH buy failed: {e}")
            raise
            
    async def _fetch_gas_price(self, chain: str) -> int:
        """Fetch current gas price"""
        if chain in self.web3_clients:
            return self.web3_clients[chain].eth.gas_price
        return 20000000000  # Default 20 gwei
    
    async def _sell_eth_token(self, wallet: Dict, token_address: str, amount: float,
                             slippage: float, gas_delta: float) -> str:
        """Execute sell on Ethereum/BSC"""
        # Placeholder - implement actual DEX interaction
        return "0x" + "0" * 64
    
    async def _buy_sol_token(self, wallet: Dict, token_address: str, amount: float,
                            slippage: float) -> str:
        """Execute buy on Solana using Raydium"""
        try:
            # Create keypair from private key
            import base58
            from solana.keypair import Keypair
            
            secret_key = base58.b58decode(wallet['private_key'])
            keypair = Keypair.from_seed(secret_key[:32])
            
            # Initialize Raydium trader
            raydium = RaydiumTrader(self.solana_client)
            
            # Execute buy
            result = await raydium.buy_token(
                keypair,
                token_address,
                amount,
                slippage
            )
            
            if result['success']:
                return result['tx_hash']
            else:
                raise Exception(result['error'])
                
        except Exception as e:
            logger.error(f"SOL buy failed: {e}")
            raise
    
    async def _sell_sol_token(self, wallet: Dict, token_address: str, amount: float,
                             slippage: float) -> str:
        """Execute sell on Solana"""
        # Placeholder - implement actual DEX interaction
        return "1" * 88
    
    async def _buy_trx_token(self, wallet: Dict, token_address: str, amount: float,
                            slippage: float) -> str:
        """Execute buy on Tron"""
        # Placeholder - implement actual DEX interaction (SunSwap, etc.)
        return "T" + "0" * 33
    
    async def _sell_trx_token(self, wallet: Dict, token_address: str, amount: float,
                             slippage: float) -> str:
        """Execute sell on Tron"""
        # Placeholder - implement actual DEX interaction
        return "T" + "0" * 33
    
    def get_active_trades(self, user_id: int) -> List[Dict]:
        """Get all active trades for a user with caching"""
        # Check cache first
        cache_key = f"active_trades:{user_id}"
        cached_trades = self.cache.get(cache_key)
        if cached_trades is not None:
            return cached_trades
            
        # Get from memory if not cached
        trades = [
            trade for trade_id, trade in self.active_trades.items()
            if trade['user_id'] == user_id
        ]
        
        # Cache for quick access
        self.cache.set(cache_key, trades, expire=10)
        return trades
    
    def get_trade_status(self, trade_id: str) -> Optional[Dict]:
        """Get status of a specific trade"""
        # Check cache first
        cached_trade = self.cache.get(f"trade:{trade_id}")
        if cached_trade:
            return cached_trade
            
        trade = self.active_trades.get(trade_id)
        if trade:
            self.cache.set(f"trade:{trade_id}", trade, expire=60)
        return trade
        
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get trading queue statistics"""
        return {
            'queue_stats': self.trading_queue.get_queue_stats(),
            'active_trades': len(self.active_trades),
            'monitored_trades': len(self.price_monitors)
        }


# Singleton instance
trading_engine = TradingEngine()