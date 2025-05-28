"""
Copy Trading Engine - Monitors and copies trades from followed wallets
"""

import asyncio
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta
import logging
from web3 import Web3
from solana.rpc.async_api import AsyncClient
import aiohttp

from config import RPC_ENDPOINTS
from trading_engine import trading_engine
from user_data import user_data

logger = logging.getLogger(__name__)


class CopyTradingEngine:
    def __init__(self):
        self.monitored_wallets: Dict[str, Set[str]] = {
            'ETH': set(),
            'SOL': set(),
            'TRX': set()
        }
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.processed_transactions: Set[str] = set()
        self.web3_clients = {
            'ETH': Web3(Web3.HTTPProvider(RPC_ENDPOINTS['ETH'][0])),
            'BSC': Web3(Web3.HTTPProvider(RPC_ENDPOINTS['BSC'][0])),
        }
        self.solana_client = AsyncClient(RPC_ENDPOINTS['SOL'][0])
        
    async def start(self):
        """Start the copy trading engine"""
        logger.info("Starting copy trading engine...")
        
        # Start monitoring task for each chain
        for chain in ['ETH', 'SOL', 'TRX']:
            if chain not in self.monitoring_tasks:
                task = asyncio.create_task(self._monitor_chain(chain))
                self.monitoring_tasks[chain] = task
    
    async def stop(self):
        """Stop the copy trading engine"""
        logger.info("Stopping copy trading engine...")
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        await asyncio.gather(*self.monitoring_tasks.values(), return_exceptions=True)
        self.monitoring_tasks.clear()
    
    def add_wallet_to_monitor(self, chain: str, wallet_address: str, user_id: int):
        """Add a wallet to monitor for copy trading"""
        if chain not in self.monitored_wallets:
            return False
        
        # Normalize address
        if chain in ['ETH', 'BSC']:
            wallet_address = Web3.to_checksum_address(wallet_address)
        
        self.monitored_wallets[chain].add(wallet_address)
        logger.info(f"Added wallet {wallet_address} to {chain} monitoring for user {user_id}")
        return True
    
    def remove_wallet_from_monitor(self, chain: str, wallet_address: str):
        """Remove a wallet from monitoring"""
        if chain in self.monitored_wallets:
            self.monitored_wallets[chain].discard(wallet_address)
            logger.info(f"Removed wallet {wallet_address} from {chain} monitoring")
    
    async def _monitor_chain(self, chain: str):
        """Monitor a specific chain for trades"""
        logger.info(f"Starting {chain} chain monitor...")
        
        while True:
            try:
                if not self.monitored_wallets[chain]:
                    await asyncio.sleep(10)
                    continue
                
                # Check for new transactions
                if chain in ['ETH', 'BSC']:
                    await self._monitor_eth_chain(chain)
                elif chain == 'SOL':
                    await self._monitor_sol_chain()
                elif chain == 'TRX':
                    await self._monitor_trx_chain()
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring {chain}: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_eth_chain(self, chain: str):
        """Monitor Ethereum-based chains"""
        try:
            w3 = self.web3_clients.get(chain)
            if not w3:
                return
            
            # Get latest block
            latest_block = w3.eth.block_number
            
            # Check transactions in recent blocks
            for block_num in range(max(0, latest_block - 2), latest_block + 1):
                block = w3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block.transactions:
                    # Check if transaction is from monitored wallet
                    if tx['from'] in self.monitored_wallets[chain]:
                        await self._process_eth_transaction(chain, tx)
                        
        except Exception as e:
            logger.error(f"Error monitoring ETH chain: {e}")
    
    async def _monitor_sol_chain(self):
        """Monitor Solana chain"""
        try:
            # Get recent signatures for each monitored wallet
            for wallet in self.monitored_wallets['SOL']:
                try:
                    # Get recent transactions
                    response = await self.solana_client.get_signatures_for_address(
                        wallet,
                        limit=10
                    )
                    
                    if response['result']:
                        for sig_info in response['result']:
                            signature = sig_info['signature']
                            
                            if signature not in self.processed_transactions:
                                # Get full transaction
                                tx = await self.solana_client.get_transaction(signature)
                                if tx['result']:
                                    await self._process_sol_transaction(tx['result'])
                                    
                except Exception as e:
                    logger.error(f"Error monitoring SOL wallet {wallet}: {e}")
                    
        except Exception as e:
            logger.error(f"Error monitoring SOL chain: {e}")
    
    async def _monitor_trx_chain(self):
        """Monitor Tron chain"""
        # Placeholder for Tron monitoring
        pass
    
    async def _process_eth_transaction(self, chain: str, tx: Dict):
        """Process an Ethereum transaction for copy trading"""
        try:
            tx_hash = tx['hash'].hex()
            
            # Skip if already processed
            if tx_hash in self.processed_transactions:
                return
            
            self.processed_transactions.add(tx_hash)
            
            # Decode transaction to check if it's a DEX trade
            if await self._is_dex_trade(chain, tx):
                trade_info = await self._decode_dex_trade(chain, tx)
                
                if trade_info:
                    logger.info(f"Detected trade: {trade_info}")
                    await self._execute_copy_trades(chain, tx['from'], trade_info)
                    
        except Exception as e:
            logger.error(f"Error processing ETH transaction: {e}")
    
    async def _process_sol_transaction(self, tx: Dict):
        """Process a Solana transaction for copy trading"""
        try:
            signature = tx['transaction']['signatures'][0]
            
            # Skip if already processed
            if signature in self.processed_transactions:
                return
            
            self.processed_transactions.add(signature)
            
            # Check if it's a DEX trade
            # This would analyze the transaction instructions
            # For now, placeholder
            
        except Exception as e:
            logger.error(f"Error processing SOL transaction: {e}")
    
    async def _is_dex_trade(self, chain: str, tx: Dict) -> bool:
        """Check if transaction is a DEX trade"""
        # Check if 'to' address is a known DEX router
        to_address = tx.get('to')
        if not to_address:
            return False
        
        to_address = to_address.lower()
        
        # Check against known DEX routers
        from config import DEX_ROUTERS
        
        for dex_routers in DEX_ROUTERS.get(chain, {}).values():
            if to_address == dex_routers.lower():
                return True
        
        return False
    
    async def _decode_dex_trade(self, chain: str, tx: Dict) -> Optional[Dict]:
        """Decode DEX trade details from transaction"""
        try:
            # This would decode the transaction input data
            # to extract trade details (token, amount, type)
            # For now, return placeholder
            
            return {
                'type': 'buy',  # or 'sell'
                'token_address': '0x...',
                'amount': 1.0,
                'from_wallet': tx['from']
            }
            
        except Exception as e:
            logger.error(f"Error decoding trade: {e}")
            return None
    
    async def _execute_copy_trades(self, chain: str, leader_wallet: str, trade_info: Dict):
        """Execute copy trades for all users following this wallet"""
        try:
            # Find all users following this wallet
            for user_id, user in user_data.items():
                if not isinstance(user_id, int):
                    continue
                
                # Check if user has this wallet in their copy trade list
                wallet_list = user.get('wallets', {}).get(chain, {}).get('GENERAL', {}).get('WALLETS_CT', {}).get('value', [])
                
                # Check if leader wallet is in user's copy list
                leader_found = False
                for wallet_info in wallet_list:
                    if isinstance(wallet_info, dict) and wallet_info.get('address', '').lower() == leader_wallet.lower():
                        leader_found = True
                        break
                
                if not leader_found:
                    continue
                
                # Check if copy trading is enabled
                copy_trade_enabled = user.get('wallets', {}).get(chain, {}).get('BUY', {}).get('bool', {}).get('COPY_TRADE', {}).get('value', False)
                
                if not copy_trade_enabled:
                    continue
                
                # Get user's trading parameters
                user_params = self._get_user_copy_params(user_id, chain)
                
                # Check if trade meets user's criteria
                if not self._meets_copy_criteria(trade_info, user_params):
                    continue
                
                # Execute copy trade
                logger.info(f"Executing copy trade for user {user_id}")
                
                if trade_info['type'] == 'buy':
                    result = await trading_engine.buy_token(
                        user_id,
                        chain,
                        trade_info['token_address'],
                        user_params['trade_amount'],
                        user_params['slippage'],
                        skip_security_check=False  # Always check security for copy trades
                    )
                else:
                    # For sells, calculate percentage based on user's holdings
                    result = await trading_engine.sell_token(
                        user_id,
                        chain,
                        trade_info['token_address'],
                        user_params['sell_percentage'],
                        user_params['slippage']
                    )
                
                if result['success']:
                    logger.info(f"Copy trade successful for user {user_id}: {result['tx_hash']}")
                    # TODO: Send notification to user
                else:
                    logger.error(f"Copy trade failed for user {user_id}: {result['error']}")
                    
        except Exception as e:
            logger.error(f"Error executing copy trades: {e}")
    
    def _get_user_copy_params(self, user_id: int, chain: str) -> Dict:
        """Get user's copy trading parameters"""
        user = user_data.get(user_id, {})
        wallet_config = user.get('wallets', {}).get(chain, {})
        
        return {
            'trade_amount': 0.1,  # Default amount - should be configurable
            'sell_percentage': 100,  # Sell same percentage as leader
            'slippage': wallet_config.get('BUY', {}).get('int', {}).get('SLIPPAGE', {}).get('value', 10),
            'min_mc': wallet_config.get('BUY', {}).get('int', {}).get('MIN_MC', {}).get('value', 0),
            'max_mc': wallet_config.get('BUY', {}).get('int', {}).get('MAX_MC', {}).get('value', 0),
            'min_liq': wallet_config.get('BUY', {}).get('int', {}).get('MIN_LIQ', {}).get('value', 0),
        }
    
    def _meets_copy_criteria(self, trade_info: Dict, user_params: Dict) -> bool:
        """Check if trade meets user's copy criteria"""
        # TODO: Check market cap, liquidity, etc.
        # For now, always return True
        return True


# Singleton instance
copy_trading_engine = CopyTradingEngine()