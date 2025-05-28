"""
Transaction Decoder - Decode DEX transactions for copy trading
"""

from web3 import Web3
from eth_abi import decode_abi
import json
import logging
from typing import Dict, Optional, List, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)

# Method signatures for common DEX functions
METHOD_SIGNATURES = {
    # Uniswap V2
    '0x7ff36ab5': 'swapExactETHForTokens',
    '0xfb3bdb41': 'swapETHForExactTokens', 
    '0x18cbafe5': 'swapExactTokensForETH',
    '0x4a25d94a': 'swapTokensForExactETH',
    '0x38ed1739': 'swapExactTokensForTokens',
    '0x8803dbee': 'swapTokensForExactTokens',
    
    # Uniswap V3
    '0x414bf389': 'exactInputSingle',
    '0xdb3e2198': 'exactOutputSingle',
    '0xc04b8d59': 'exactInput',
    '0xf28c0498': 'exactOutput',
    
    # PancakeSwap (same as Uniswap V2)
    '0xf305d719': 'addLiquidityETH',
    '0xe8e33700': 'addLiquidity',
    '0xbaa2abde': 'removeLiquidity',
    '0x02751cec': 'removeLiquidityETH',
    
    # 1inch
    '0x7c025200': 'swap',
    '0x2e95b6c8': 'unoswap',
    
    # Generic
    '0x095ea7b3': 'approve',
    '0xa9059cbb': 'transfer',
}

# Uniswap V2 swap event topic
SWAP_EVENT_TOPIC = '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'

# Transfer event topic  
TRANSFER_EVENT_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'


class TransactionDecoder:
    """Decode DEX transactions to extract trade information"""
    
    def __init__(self, web3: Web3):
        self.w3 = web3
        
        # Load router ABIs
        self.router_abis = {}
        self._load_abis()
    
    def _load_abis(self):
        """Load DEX router ABIs"""
        try:
            # Load Uniswap V2 ABI
            with open('dex/uniswap_v2_abi.json', 'r') as f:
                self.router_abis['uniswap_v2'] = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load ABIs: {e}")
    
    async def decode_transaction(self, tx_hash: str, chain: str = 'ETH') -> Optional[Dict]:
        """Decode a transaction to extract trade details"""
        try:
            # Get transaction
            tx = self.w3.eth.get_transaction(tx_hash)
            if not tx:
                return None
            
            # Get transaction receipt for logs
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if not receipt:
                return None
            
            # Check if it's a DEX transaction
            method_id = tx['input'][:10]
            method_name = METHOD_SIGNATURES.get(method_id)
            
            if not method_name:
                return None
            
            # Decode based on method
            trade_info = None
            
            if method_name in ['swapExactETHForTokens', 'swapETHForExactTokens']:
                trade_info = self._decode_eth_for_tokens(tx, receipt, method_name)
            elif method_name in ['swapExactTokensForETH', 'swapTokensForExactETH']:
                trade_info = self._decode_tokens_for_eth(tx, receipt, method_name)
            elif method_name in ['swapExactTokensForTokens', 'swapTokensForExactTokens']:
                trade_info = self._decode_tokens_for_tokens(tx, receipt, method_name)
            elif method_name == 'exactInputSingle':
                trade_info = self._decode_uniswap_v3_single(tx, receipt)
            
            if trade_info:
                trade_info.update({
                    'tx_hash': tx_hash,
                    'from_address': tx['from'],
                    'to_address': tx['to'],
                    'gas_price': self.w3.from_wei(tx['gasPrice'], 'gwei'),
                    'method': method_name,
                    'block_number': tx['blockNumber'],
                    'chain': chain
                })
            
            return trade_info
            
        except Exception as e:
            logger.error(f"Failed to decode transaction {tx_hash}: {e}")
            return None
    
    def _decode_eth_for_tokens(self, tx: Dict, receipt: Dict, method: str) -> Optional[Dict]:
        """Decode ETH to token swap"""
        try:
            # Decode input data
            if method == 'swapExactETHForTokens':
                # Parameters: amountOutMin, path, to, deadline
                params = decode_abi(
                    ['uint256', 'address[]', 'address', 'uint256'],
                    bytes.fromhex(tx['input'][10:])
                )
                amount_out_min = params[0]
                path = params[1]
                
                return {
                    'type': 'buy',
                    'token_in': 'ETH',
                    'token_out': path[-1],  # Last token in path
                    'amount_in': float(self.w3.from_wei(tx['value'], 'ether')),
                    'min_amount_out': amount_out_min,
                    'path': path,
                    'exact_input': True
                }
            
            elif method == 'swapETHForExactTokens':
                # Parameters: amountOut, path, to, deadline
                params = decode_abi(
                    ['uint256', 'address[]', 'address', 'uint256'],
                    bytes.fromhex(tx['input'][10:])
                )
                amount_out = params[0]
                path = params[1]
                
                return {
                    'type': 'buy',
                    'token_in': 'ETH',
                    'token_out': path[-1],
                    'amount_in': float(self.w3.from_wei(tx['value'], 'ether')),
                    'exact_amount_out': amount_out,
                    'path': path,
                    'exact_input': False
                }
                
        except Exception as e:
            logger.error(f"Failed to decode ETH for tokens: {e}")
            return None
    
    def _decode_tokens_for_eth(self, tx: Dict, receipt: Dict, method: str) -> Optional[Dict]:
        """Decode token to ETH swap"""
        try:
            if method == 'swapExactTokensForETH':
                # Parameters: amountIn, amountOutMin, path, to, deadline
                params = decode_abi(
                    ['uint256', 'uint256', 'address[]', 'address', 'uint256'],
                    bytes.fromhex(tx['input'][10:])
                )
                amount_in = params[0]
                amount_out_min = params[1]
                path = params[2]
                
                return {
                    'type': 'sell',
                    'token_in': path[0],  # First token in path
                    'token_out': 'ETH',
                    'amount_in': amount_in,
                    'min_amount_out': float(self.w3.from_wei(amount_out_min, 'ether')),
                    'path': path,
                    'exact_input': True
                }
                
        except Exception as e:
            logger.error(f"Failed to decode tokens for ETH: {e}")
            return None
    
    def _decode_tokens_for_tokens(self, tx: Dict, receipt: Dict, method: str) -> Optional[Dict]:
        """Decode token to token swap"""
        try:
            if method == 'swapExactTokensForTokens':
                # Parameters: amountIn, amountOutMin, path, to, deadline
                params = decode_abi(
                    ['uint256', 'uint256', 'address[]', 'address', 'uint256'],
                    bytes.fromhex(tx['input'][10:])
                )
                amount_in = params[0]
                amount_out_min = params[1]
                path = params[2]
                
                return {
                    'type': 'swap',
                    'token_in': path[0],
                    'token_out': path[-1],
                    'amount_in': amount_in,
                    'min_amount_out': amount_out_min,
                    'path': path,
                    'exact_input': True
                }
                
        except Exception as e:
            logger.error(f"Failed to decode token swap: {e}")
            return None
    
    def _decode_uniswap_v3_single(self, tx: Dict, receipt: Dict) -> Optional[Dict]:
        """Decode Uniswap V3 single swap"""
        try:
            # Decode exactInputSingle parameters
            # struct: tokenIn, tokenOut, fee, recipient, deadline, amountIn, amountOutMinimum, sqrtPriceLimitX96
            params = decode_abi(
                ['address', 'address', 'uint24', 'address', 'uint256', 'uint256', 'uint256', 'uint160'],
                bytes.fromhex(tx['input'][10:])
            )
            
            token_in = params[0]
            token_out = params[1]
            amount_in = params[5]
            amount_out_min = params[6]
            
            # Check if ETH is involved
            weth = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
            
            if token_in.lower() == weth.lower():
                trade_type = 'buy'
                token_in = 'ETH'
                amount_in = float(self.w3.from_wei(amount_in, 'ether'))
            elif token_out.lower() == weth.lower():
                trade_type = 'sell'
                token_out = 'ETH'
            else:
                trade_type = 'swap'
            
            return {
                'type': trade_type,
                'token_in': token_in,
                'token_out': token_out,
                'amount_in': amount_in,
                'min_amount_out': amount_out_min,
                'exact_input': True,
                'dex': 'uniswap_v3'
            }
            
        except Exception as e:
            logger.error(f"Failed to decode Uniswap V3: {e}")
            return None
    
    def extract_tokens_from_logs(self, receipt: Dict) -> Dict[str, List[Dict]]:
        """Extract token transfers from transaction logs"""
        transfers = {
            'incoming': [],
            'outgoing': []
        }
        
        try:
            for log in receipt['logs']:
                # Check if it's a Transfer event
                if log['topics'][0].hex() == TRANSFER_EVENT_TOPIC:
                    # Decode transfer
                    from_address = '0x' + log['topics'][1].hex()[26:]
                    to_address = '0x' + log['topics'][2].hex()[26:]
                    amount = int(log['data'], 16)
                    
                    transfer = {
                        'token': log['address'],
                        'from': from_address,
                        'to': to_address,
                        'amount': amount
                    }
                    
                    # Categorize based on transaction sender
                    if from_address.lower() == receipt['from'].lower():
                        transfers['outgoing'].append(transfer)
                    elif to_address.lower() == receipt['from'].lower():
                        transfers['incoming'].append(transfer)
                        
        except Exception as e:
            logger.error(f"Failed to extract transfers: {e}")
        
        return transfers
    
    def calculate_price_impact(self, amount_in: float, amount_out: float,
                             expected_out: float) -> float:
        """Calculate price impact of a trade"""
        if expected_out == 0:
            return 0
        
        actual_price = amount_in / amount_out
        expected_price = amount_in / expected_out
        
        price_impact = ((actual_price - expected_price) / expected_price) * 100
        return abs(price_impact)
    
    async def decode_pending_transaction(self, tx_data: Dict) -> Optional[Dict]:
        """Decode a pending transaction from mempool"""
        try:
            # Check method
            method_id = tx_data.get('input', '')[:10]
            method_name = METHOD_SIGNATURES.get(method_id)
            
            if not method_name:
                return None
            
            # Basic info that we can extract without receipt
            trade_info = {
                'type': 'pending',
                'method': method_name,
                'from_address': tx_data.get('from'),
                'to_address': tx_data.get('to'),
                'gas_price': float(self.w3.from_wei(tx_data.get('gasPrice', 0), 'gwei')),
                'max_fee': float(self.w3.from_wei(tx_data.get('maxFeePerGas', 0), 'gwei')),
                'value': float(self.w3.from_wei(tx_data.get('value', 0), 'ether'))
            }
            
            # Try to decode input data
            if method_name in ['swapExactETHForTokens', 'swapETHForExactTokens']:
                try:
                    params = decode_abi(
                        ['uint256', 'address[]', 'address', 'uint256'],
                        bytes.fromhex(tx_data['input'][10:])
                    )
                    trade_info.update({
                        'token_out': params[1][-1],
                        'amount_in': trade_info['value'],
                        'path': params[1]
                    })
                except:
                    pass
            
            return trade_info
            
        except Exception as e:
            logger.error(f"Failed to decode pending tx: {e}")
            return None


# Usage example
async def decode_example():
    w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
    decoder = TransactionDecoder(w3)
    
    # Decode a known Uniswap transaction
    tx_hash = '0x...'  # Replace with actual tx hash
    trade_info = await decoder.decode_transaction(tx_hash)
    
    if trade_info:
        print(f"Trade Type: {trade_info['type']}")
        print(f"Token In: {trade_info['token_in']}")
        print(f"Token Out: {trade_info['token_out']}")
        print(f"Amount: {trade_info['amount_in']}")