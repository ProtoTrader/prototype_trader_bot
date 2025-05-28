"""
Uniswap V2/V3 integration for Ethereum trading
"""

from web3 import Web3
from decimal import Decimal
import json
import asyncio
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Uniswap V2 Router ABI (simplified)
UNISWAP_V2_ROUTER_ABI = json.loads('''[
    {
        "name": "swapExactETHForTokens",
        "type": "function",
        "inputs": [
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}]
    },
    {
        "name": "swapExactTokensForETH",
        "type": "function",
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}]
    },
    {
        "name": "getAmountsOut",
        "type": "function",
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"}
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view"
    }
]''')

# ERC20 ABI (simplified)
ERC20_ABI = json.loads('''[
    {
        "name": "approve",
        "type": "function",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": [{"name": "", "type": "bool"}]
    },
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "decimals",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view"
    }
]''')


class UniswapTrader:
    def __init__(self, web3: Web3, router_address: str, weth_address: str):
        self.w3 = web3
        self.router = self.w3.eth.contract(address=router_address, abi=UNISWAP_V2_ROUTER_ABI)
        self.weth_address = weth_address
    
    async def buy_token(self, wallet_address: str, private_key: str, 
                       token_address: str, eth_amount: float, 
                       slippage: float = 10.0, gas_price_gwei: Optional[float] = None) -> Dict:
        """Buy token with ETH"""
        try:
            # Convert ETH amount to Wei
            amount_in_wei = self.w3.to_wei(eth_amount, 'ether')
            
            # Create path [WETH, TOKEN]
            path = [self.weth_address, Web3.to_checksum_address(token_address)]
            
            # Get expected output amount
            amounts_out = self.router.functions.getAmountsOut(amount_in_wei, path).call()
            expected_out = amounts_out[-1]
            
            # Calculate minimum output with slippage
            min_out = int(expected_out * (100 - slippage) / 100)
            
            # Set deadline (10 minutes from now)
            deadline = int(asyncio.get_event_loop().time()) + 600
            
            # Build transaction
            tx = self.router.functions.swapExactETHForTokens(
                min_out,
                path,
                wallet_address,
                deadline
            ).build_transaction({
                'from': wallet_address,
                'value': amount_in_wei,
                'gas': 300000,  # Estimate gas properly in production
                'gasPrice': self.w3.to_wei(gas_price_gwei or 50, 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(wallet_address),
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Buy transaction sent: {tx_hash.hex()}")
            
            return {
                'success': True,
                'tx_hash': tx_hash.hex(),
                'expected_tokens': expected_out,
                'eth_spent': eth_amount
            }
            
        except Exception as e:
            logger.error(f"Buy failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def sell_token(self, wallet_address: str, private_key: str,
                        token_address: str, token_amount: float,
                        slippage: float = 10.0, gas_price_gwei: Optional[float] = None) -> Dict:
        """Sell token for ETH"""
        try:
            token_address = Web3.to_checksum_address(token_address)
            token_contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            
            # Get token decimals
            decimals = token_contract.functions.decimals().call()
            amount_in_wei = int(token_amount * (10 ** decimals))
            
            # Approve router to spend tokens
            approve_tx = token_contract.functions.approve(
                self.router.address,
                amount_in_wei
            ).build_transaction({
                'from': wallet_address,
                'gas': 100000,
                'gasPrice': self.w3.to_wei(gas_price_gwei or 50, 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(wallet_address),
            })
            
            signed_approve = self.w3.eth.account.sign_transaction(approve_tx, private_key)
            approve_hash = self.w3.eth.send_raw_transaction(signed_approve.rawTransaction)
            
            # Wait for approval
            self.w3.eth.wait_for_transaction_receipt(approve_hash)
            
            # Create path [TOKEN, WETH]
            path = [token_address, self.weth_address]
            
            # Get expected output amount
            amounts_out = self.router.functions.getAmountsOut(amount_in_wei, path).call()
            expected_out = amounts_out[-1]
            
            # Calculate minimum output with slippage
            min_out = int(expected_out * (100 - slippage) / 100)
            
            # Set deadline
            deadline = int(asyncio.get_event_loop().time()) + 600
            
            # Build sell transaction
            tx = self.router.functions.swapExactTokensForETH(
                amount_in_wei,
                min_out,
                path,
                wallet_address,
                deadline
            ).build_transaction({
                'from': wallet_address,
                'gas': 300000,
                'gasPrice': self.w3.to_wei(gas_price_gwei or 50, 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(wallet_address) + 1,
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Sell transaction sent: {tx_hash.hex()}")
            
            return {
                'success': True,
                'tx_hash': tx_hash.hex(),
                'expected_eth': self.w3.from_wei(expected_out, 'ether'),
                'tokens_sold': token_amount
            }
            
        except Exception as e:
            logger.error(f"Sell failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_token_price(self, token_address: str, amount: float = 1.0) -> Optional[float]:
        """Get current token price in ETH"""
        try:
            token_address = Web3.to_checksum_address(token_address)
            token_contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            
            # Get decimals
            decimals = token_contract.functions.decimals().call()
            amount_in_wei = int(amount * (10 ** decimals))
            
            # Get price from router
            path = [token_address, self.weth_address]
            amounts_out = self.router.functions.getAmountsOut(amount_in_wei, path).call()
            
            eth_amount = self.w3.from_wei(amounts_out[-1], 'ether')
            return float(eth_amount)
            
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            return None