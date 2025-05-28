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

logger = logging.getLogger(__name__)


class TradingEngine:
    """Manages trading operations across different chains"""
    
    def __init__(self):
        self.active_trades = {}
        self.price_monitors = {}
        self.web3_clients = {
            'ETH': Web3(Web3.HTTPProvider('https://eth.llamarpc.com')),
            'BSC': Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
        }
        self.solana_client = AsyncClient("https://api.mainnet-beta.solana.com")
        
    async def buy_token(self, user_id: int, chain: str, token_address: str, 
                       amount: float, slippage: float = 10.0, gas_delta: float = 0.001) -> Dict:
        """Execute a buy order"""
        try:
            # Get user's wallet
            wallet = self._get_user_wallet(user_id, chain)
            if not wallet:
                return {'success': False, 'error': 'No wallet connected'}
            
            # Prepare transaction based on chain
            if chain == 'ETH':
                tx_hash = await self._buy_eth_token(wallet, token_address, amount, slippage, gas_delta)
            elif chain == 'SOL':
                tx_hash = await self._buy_sol_token(wallet, token_address, amount, slippage)
            elif chain == 'TRX':
                tx_hash = await self._buy_trx_token(wallet, token_address, amount, slippage)
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
    
    async def _get_token_price(self, chain: str, token_address: str) -> Optional[float]:
        """Get current token price"""
        # This is a placeholder - implement actual price fetching
        # You would integrate with DEX APIs like Uniswap, PancakeSwap, Raydium, etc.
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
    
    async def _buy_eth_token(self, wallet: Dict, token_address: str, amount: float, 
                            slippage: float, gas_delta: float) -> str:
        """Execute buy on Ethereum/BSC"""
        # Placeholder - implement actual DEX interaction
        # This would use Uniswap/PancakeSwap Router contracts
        return "0x" + "0" * 64
    
    async def _sell_eth_token(self, wallet: Dict, token_address: str, amount: float,
                             slippage: float, gas_delta: float) -> str:
        """Execute sell on Ethereum/BSC"""
        # Placeholder - implement actual DEX interaction
        return "0x" + "0" * 64
    
    async def _buy_sol_token(self, wallet: Dict, token_address: str, amount: float,
                            slippage: float) -> str:
        """Execute buy on Solana"""
        # Placeholder - implement actual DEX interaction (Raydium, Orca, etc.)
        return "1" * 88
    
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
        """Get all active trades for a user"""
        return [
            trade for trade_id, trade in self.active_trades.items()
            if trade['user_id'] == user_id
        ]
    
    def get_trade_status(self, trade_id: str) -> Optional[Dict]:
        """Get status of a specific trade"""
        return self.active_trades.get(trade_id)


# Singleton instance
trading_engine = TradingEngine()