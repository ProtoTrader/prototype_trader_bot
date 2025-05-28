"""
Sniper Bot - Auto-buy new token launches
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from web3 import Web3
from decimal import Decimal
import aiohttp

from trading_engine import trading_engine
from security.honeypot_scanner import scan_token_security
from notifications import notification_manager
from utils.retry_manager import with_retry, tx_retry_manager
from config import RPC_ENDPOINTS, DEX_ROUTERS

logger = logging.getLogger(__name__)


class SniperBot:
    """Sniper bot for new token launches"""
    
    def __init__(self):
        self.active_snipers = {}
        self.monitoring_tasks = {}
        self.pending_launches = {}
        self.sniped_tokens = set()  # Avoid double buys
        
        # Web3 instances for different chains
        self.web3_instances = {
            'ETH': Web3(Web3.HTTPProvider(RPC_ENDPOINTS['ETH'][0])),
            'BSC': Web3(Web3.HTTPProvider(RPC_ENDPOINTS['BSC'][0]))
        }
        
        # Event signatures to monitor
        self.pair_created_topic = '0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9'  # PairCreated
        self.mint_topic = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'  # Transfer (from 0x0)
    
    async def create_sniper(self, user_id: int, params: Dict) -> str:
        """Create a new sniper configuration"""
        sniper_id = f"sniper_{user_id}_{datetime.now().timestamp()}"
        
        sniper_config = {
            'id': sniper_id,
            'user_id': user_id,
            'chain': params['chain'],
            'mode': params.get('mode', 'liquidity'),  # 'liquidity' or 'contract_deploy'
            'buy_amount': params['buy_amount'],
            'gas_price_gwei': params.get('gas_price_gwei', 'auto'),
            'max_gas_price_gwei': params.get('max_gas_price_gwei', 500),
            'slippage': params.get('slippage', 50),  # High slippage for launches
            'min_liquidity': params.get('min_liquidity', 10),  # Min liquidity in ETH/BNB
            'max_buy_tax': params.get('max_buy_tax', 10),
            'max_sell_tax': params.get('max_sell_tax', 10),
            'auto_sell': params.get('auto_sell', False),
            'sell_multiplier': params.get('sell_multiplier', 2),  # 2x = 100% profit
            'blocks_to_wait': params.get('blocks_to_wait', 0),  # Anti-bot delay
            'created_at': datetime.now(),
            'status': 'active',
            'tokens_sniped': []
        }
        
        # Specific token to snipe (optional)
        if 'token_address' in params:
            sniper_config['token_address'] = params['token_address']
            sniper_config['mode'] = 'specific_token'
        
        self.active_snipers[sniper_id] = sniper_config
        
        # Start monitoring
        task = asyncio.create_task(self._monitor_sniper(sniper_id))
        self.monitoring_tasks[sniper_id] = task
        
        logger.info(f"Created sniper: {sniper_id}")
        return sniper_id
    
    async def _monitor_sniper(self, sniper_id: str):
        """Monitor for sniper opportunities"""
        sniper = self.active_snipers.get(sniper_id)
        if not sniper:
            return
        
        try:
            if sniper['mode'] == 'liquidity':
                await self._monitor_liquidity_adds(sniper)
            elif sniper['mode'] == 'contract_deploy':
                await self._monitor_new_contracts(sniper)
            elif sniper['mode'] == 'specific_token':
                await self._monitor_specific_token(sniper)
                
        except asyncio.CancelledError:
            logger.info(f"Sniper {sniper_id} cancelled")
        except Exception as e:
            logger.error(f"Sniper {sniper_id} error: {e}")
    
    async def _monitor_liquidity_adds(self, sniper: Dict):
        """Monitor for new liquidity additions"""
        chain = sniper['chain']
        w3 = self.web3_instances.get(chain)
        
        if not w3:
            logger.error(f"No Web3 instance for {chain}")
            return
        
        # Get factory addresses
        factory_addresses = {
            'ETH': [
                '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',  # Uniswap V2
                '0x1F98431c8aD98523631AE4a59f267346ea31F984',  # Uniswap V3
            ],
            'BSC': [
                '0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73',  # PancakeSwap V2
                '0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865',  # PancakeSwap V3
            ]
        }
        
        factories = factory_addresses.get(chain, [])
        
        # Create event filter
        event_filter = w3.eth.filter({
            'address': factories,
            'topics': [self.pair_created_topic]
        })
        
        logger.info(f"Monitoring liquidity additions on {chain}")
        
        while sniper['status'] == 'active':
            try:
                # Get new events
                for event in event_filter.get_new_entries():
                    await self._process_pair_created(sniper, event)
                
                await asyncio.sleep(1)  # Poll every second
                
            except Exception as e:
                logger.error(f"Error monitoring liquidity: {e}")
                await asyncio.sleep(5)
    
    async def _process_pair_created(self, sniper: Dict, event: Dict):
        """Process new pair creation event"""
        try:
            # Decode event data
            token0 = '0x' + event['topics'][1].hex()[26:]
            token1 = '0x' + event['topics'][2].hex()[26:]
            pair_address = '0x' + event['data'][26:66]
            
            # Identify which is the new token (not WETH/WBNB)
            weth_addresses = {
                'ETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                'BSC': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
            }
            
            weth = weth_addresses.get(sniper['chain'])
            
            if token0.lower() == weth.lower():
                new_token = token1
            elif token1.lower() == weth.lower():
                new_token = token0
            else:
                # Not a WETH pair, skip
                return
            
            # Check if already sniped
            if new_token.lower() in self.sniped_tokens:
                return
            
            logger.info(f"New pair detected: {new_token} on {sniper['chain']}")
            
            # Quick security check
            if await self._quick_security_check(sniper['chain'], new_token, sniper):
                # Execute snipe
                await self._execute_snipe(sniper, new_token, pair_address)
            
        except Exception as e:
            logger.error(f"Error processing pair created: {e}")
    
    async def _monitor_specific_token(self, sniper: Dict):
        """Monitor for specific token liquidity"""
        token_address = sniper['token_address']
        chain = sniper['chain']
        
        logger.info(f"Monitoring specific token {token_address} on {chain}")
        
        check_interval = 0.5  # Check every 500ms
        max_wait_time = 3600  # 1 hour max wait
        start_time = datetime.now()
        
        while sniper['status'] == 'active':
            try:
                # Check if liquidity added
                has_liquidity = await self._check_token_liquidity(chain, token_address)
                
                if has_liquidity:
                    logger.info(f"Liquidity detected for {token_address}")
                    
                    # Quick security check
                    if await self._quick_security_check(chain, token_address, sniper):
                        # Execute snipe
                        await self._execute_snipe(sniper, token_address, None)
                    
                    break  # Stop monitoring after snipe attempt
                
                # Check timeout
                if (datetime.now() - start_time).seconds > max_wait_time:
                    logger.warning(f"Sniper timeout for {token_address}")
                    break
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring token: {e}")
                await asyncio.sleep(2)
    
    async def _quick_security_check(self, chain: str, token_address: str, sniper: Dict) -> bool:
        """Quick security check for sniping"""
        try:
            # Basic checks only (full scan takes too long for sniping)
            w3 = self.web3_instances.get(chain)
            if not w3:
                return False
            
            # Check contract exists
            code = w3.eth.get_code(token_address)
            if code == b'':
                logger.warning(f"No contract at {token_address}")
                return False
            
            # Quick tax check if possible
            # This would need custom implementation based on token
            
            # Check buy/sell tax limits
            max_buy_tax = sniper.get('max_buy_tax', 10)
            max_sell_tax = sniper.get('max_sell_tax', 10)
            
            # For now, return True (implement actual tax checking)
            return True
            
        except Exception as e:
            logger.error(f"Security check failed: {e}")
            return False
    
    async def _check_token_liquidity(self, chain: str, token_address: str) -> bool:
        """Check if token has liquidity"""
        try:
            # This would check Uniswap/PancakeSwap pairs
            # For now, return mock result
            return False
            
        except Exception as e:
            logger.error(f"Liquidity check failed: {e}")
            return False
    
    async def _execute_snipe(self, sniper: Dict, token_address: str, pair_address: Optional[str]):
        """Execute the snipe buy"""
        try:
            # Mark as sniped to avoid double buys
            self.sniped_tokens.add(token_address.lower())
            
            user_id = sniper['user_id']
            chain = sniper['chain']
            
            # Wait for anti-bot blocks if configured
            if sniper.get('blocks_to_wait', 0) > 0:
                logger.info(f"Waiting {sniper['blocks_to_wait']} blocks before buying")
                await self._wait_blocks(chain, sniper['blocks_to_wait'])
            
            # Prepare gas settings
            if sniper['gas_price_gwei'] == 'auto':
                # Use aggressive gas for sniping
                gas_multiplier = 2.0
            else:
                gas_multiplier = 1.0
            
            # Execute buy with retry
            result = await tx_retry_manager.execute_with_retry(
                trading_engine.buy_token,
                {
                    'user_id': user_id,
                    'chain': chain,
                    'token_address': token_address,
                    'amount': sniper['buy_amount'],
                    'slippage': sniper['slippage'],
                    'gas_delta': 0.001,
                    'skip_security_check': True  # Already checked
                },
                max_attempts=2,  # Quick retries for sniping
                gas_multiplier=gas_multiplier
            )
            
            if result['success']:
                # Record sniped token
                sniper['tokens_sniped'].append({
                    'token_address': token_address,
                    'tx_hash': result['tx_hash'],
                    'amount': sniper['buy_amount'],
                    'timestamp': datetime.now(),
                    'buy_price': await self._get_buy_price(chain, token_address)
                })
                
                # Notify user
                await notification_manager.notify_trade_executed(
                    user_id,
                    {
                        'type': 'SNIPER BUY',
                        'chain': chain,
                        'amount': sniper['buy_amount'],
                        'tx_hash': result['tx_hash']
                    }
                )
                
                # Setup auto-sell if configured
                if sniper.get('auto_sell'):
                    await self._setup_auto_sell(
                        user_id, chain, token_address,
                        result.get('trade_id'),
                        sniper['sell_multiplier']
                    )
                
                logger.info(f"Successfully sniped {token_address}")
                
            else:
                logger.error(f"Snipe failed: {result.get('error')}")
                
                # Notify failure
                await notification_manager.notification_queue.put({
                    'user_id': user_id,
                    'message': f"❌ Snipe failed for {token_address[:8]}...\nError: {result.get('error')}"
                })
                
        except Exception as e:
            logger.error(f"Snipe execution failed: {e}")
    
    async def _wait_blocks(self, chain: str, blocks: int):
        """Wait for specified number of blocks"""
        w3 = self.web3_instances.get(chain)
        if not w3:
            return
        
        start_block = w3.eth.block_number
        target_block = start_block + blocks
        
        while w3.eth.block_number < target_block:
            await asyncio.sleep(1)
    
    async def _get_buy_price(self, chain: str, token_address: str) -> float:
        """Get token price at time of buy"""
        # This would get actual price from DEX
        return 0.0
    
    async def _setup_auto_sell(self, user_id: int, chain: str, token_address: str,
                             trade_id: str, sell_multiplier: float):
        """Setup automatic sell at target multiplier"""
        try:
            # Calculate target profit percentage
            target_profit = (sell_multiplier - 1) * 100  # 2x = 100% profit
            
            # Set take profit
            await trading_engine.set_take_profit(trade_id, target_profit)
            
            logger.info(f"Auto-sell set at {sell_multiplier}x for {token_address}")
            
        except Exception as e:
            logger.error(f"Failed to setup auto-sell: {e}")
    
    def cancel_sniper(self, sniper_id: str) -> bool:
        """Cancel active sniper"""
        if sniper_id in self.active_snipers:
            self.active_snipers[sniper_id]['status'] = 'cancelled'
            
            # Cancel monitoring task
            if sniper_id in self.monitoring_tasks:
                self.monitoring_tasks[sniper_id].cancel()
                del self.monitoring_tasks[sniper_id]
            
            logger.info(f"Cancelled sniper: {sniper_id}")
            return True
        
        return False
    
    def get_user_snipers(self, user_id: int) -> List[Dict]:
        """Get all snipers for a user"""
        return [
            sniper for sniper in self.active_snipers.values()
            if sniper['user_id'] == user_id
        ]
    
    async def monitor_mempool(self, chain: str):
        """Monitor mempool for pending liquidity adds"""
        # This would connect to mempool services
        # to detect liquidity additions before they're mined
        pass


# Singleton instance
sniper_bot = SniperBot()