"""
Raydium integration for Solana trading
"""

from solana.rpc.async_api import AsyncClient
from solana.keypair import Keypair
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solana.publickey import PublicKey
import base58
from typing import Dict, Optional
import logging
import struct

logger = logging.getLogger(__name__)

# Raydium Program IDs
RAYDIUM_AMM_PROGRAM = PublicKey("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
SERUM_PROGRAM = PublicKey("9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin")

# System Program
SYSTEM_PROGRAM = PublicKey("11111111111111111111111111111111")
TOKEN_PROGRAM = PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM = PublicKey("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

# SOL Mint
WSOL_MINT = PublicKey("So11111111111111111111111111111111111111112")


class RaydiumTrader:
    def __init__(self, client: AsyncClient):
        self.client = client
    
    async def buy_token(self, wallet_keypair: Keypair, token_mint: str, 
                       sol_amount: float, slippage: float = 10.0) -> Dict:
        """Buy token with SOL on Raydium"""
        try:
            wallet_pubkey = wallet_keypair.public_key
            token_mint_pubkey = PublicKey(token_mint)
            
            # Get pool info for the token
            pool_info = await self._get_pool_info(token_mint_pubkey)
            if not pool_info:
                return {'success': False, 'error': 'Pool not found'}
            
            # Convert SOL to lamports
            amount_in_lamports = int(sol_amount * 1e9)
            
            # Calculate expected output with slippage
            expected_out = await self._calculate_swap_amount(
                pool_info, 
                amount_in_lamports, 
                True  # SOL to Token
            )
            
            min_out = int(expected_out * (100 - slippage) / 100)
            
            # Create swap instruction
            swap_ix = await self._create_swap_instruction(
                wallet_pubkey,
                pool_info,
                amount_in_lamports,
                min_out,
                True  # Buy
            )
            
            # Build and send transaction
            recent_blockhash = await self.client.get_recent_blockhash()
            tx = Transaction()
            tx.add(swap_ix)
            tx.recent_blockhash = recent_blockhash['result']['value']['blockhash']
            tx.fee_payer = wallet_pubkey
            
            # Sign and send
            tx.sign(wallet_keypair)
            response = await self.client.send_transaction(tx, wallet_keypair)
            
            if response['result']:
                logger.info(f"Buy transaction sent: {response['result']}")
                return {
                    'success': True,
                    'tx_hash': response['result'],
                    'expected_tokens': expected_out,
                    'sol_spent': sol_amount
                }
            else:
                return {'success': False, 'error': 'Transaction failed'}
                
        except Exception as e:
            logger.error(f"Buy failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def sell_token(self, wallet_keypair: Keypair, token_mint: str,
                        token_amount: float, slippage: float = 10.0) -> Dict:
        """Sell token for SOL on Raydium"""
        try:
            wallet_pubkey = wallet_keypair.public_key
            token_mint_pubkey = PublicKey(token_mint)
            
            # Get pool info for the token
            pool_info = await self._get_pool_info(token_mint_pubkey)
            if not pool_info:
                return {'success': False, 'error': 'Pool not found'}
            
            # Get token decimals and convert amount
            token_info = await self._get_token_info(token_mint_pubkey)
            amount_in = int(token_amount * (10 ** token_info['decimals']))
            
            # Calculate expected output with slippage
            expected_out = await self._calculate_swap_amount(
                pool_info,
                amount_in,
                False  # Token to SOL
            )
            
            min_out = int(expected_out * (100 - slippage) / 100)
            
            # Create swap instruction
            swap_ix = await self._create_swap_instruction(
                wallet_pubkey,
                pool_info,
                amount_in,
                min_out,
                False  # Sell
            )
            
            # Build and send transaction
            recent_blockhash = await self.client.get_recent_blockhash()
            tx = Transaction()
            tx.add(swap_ix)
            tx.recent_blockhash = recent_blockhash['result']['value']['blockhash']
            tx.fee_payer = wallet_pubkey
            
            # Sign and send
            tx.sign(wallet_keypair)
            response = await self.client.send_transaction(tx, wallet_keypair)
            
            if response['result']:
                logger.info(f"Sell transaction sent: {response['result']}")
                return {
                    'success': True,
                    'tx_hash': response['result'],
                    'expected_sol': expected_out / 1e9,
                    'tokens_sold': token_amount
                }
            else:
                return {'success': False, 'error': 'Transaction failed'}
                
        except Exception as e:
            logger.error(f"Sell failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_token_price(self, token_mint: str) -> Optional[float]:
        """Get current token price in SOL"""
        try:
            token_mint_pubkey = PublicKey(token_mint)
            pool_info = await self._get_pool_info(token_mint_pubkey)
            
            if not pool_info:
                return None
            
            # Calculate price based on pool reserves
            sol_reserve = pool_info['sol_reserve']
            token_reserve = pool_info['token_reserve']
            
            if token_reserve > 0:
                price = sol_reserve / token_reserve / 1e9  # Convert lamports to SOL
                return price
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            return None
    
    async def _get_pool_info(self, token_mint: PublicKey) -> Optional[Dict]:
        """Get Raydium pool information for a token"""
        # This is a simplified version - in production, you would:
        # 1. Query all Raydium pools
        # 2. Find the pool with the highest liquidity for the token
        # 3. Parse the pool account data
        # For now, return placeholder data
        return {
            'pool_address': 'pool_address_placeholder',
            'sol_reserve': 1000 * 1e9,  # 1000 SOL
            'token_reserve': 1000000,    # 1M tokens
            'pool_mint': 'pool_mint_placeholder'
        }
    
    async def _get_token_info(self, token_mint: PublicKey) -> Dict:
        """Get token information"""
        # In production, query the token mint account
        # For now, return default decimals
        return {'decimals': 9}
    
    async def _calculate_swap_amount(self, pool_info: Dict, amount_in: int, 
                                   is_sol_to_token: bool) -> int:
        """Calculate expected output amount for swap"""
        # Simplified AMM calculation (constant product)
        if is_sol_to_token:
            reserve_in = pool_info['sol_reserve']
            reserve_out = pool_info['token_reserve']
        else:
            reserve_in = pool_info['token_reserve']
            reserve_out = pool_info['sol_reserve']
        
        # Apply 0.25% Raydium fee
        amount_in_with_fee = amount_in * 9975
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 10000) + amount_in_with_fee
        
        return numerator // denominator
    
    async def _create_swap_instruction(self, wallet: PublicKey, pool_info: Dict,
                                     amount_in: int, min_out: int, is_buy: bool):
        """Create Raydium swap instruction"""
        # This is a placeholder - actual implementation would:
        # 1. Create proper instruction data
        # 2. Include all necessary accounts
        # 3. Set correct program ID
        # For now, return a simple transfer instruction as placeholder
        return transfer(
            TransferParams(
                from_pubkey=wallet,
                to_pubkey=PublicKey(pool_info['pool_address']),
                lamports=1000  # Placeholder
            )
        )