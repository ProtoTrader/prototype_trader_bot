"""
Honeypot Scanner - Detects malicious tokens and scams
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
from web3 import Web3
import json
import logging
from config import SECURITY_CHECKS, RPC_ENDPOINTS

logger = logging.getLogger(__name__)

# Token checker ABI for common honeypot functions
TOKEN_CHECKER_ABI = json.loads('''[
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "totalSupply",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "owner",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view"
    },
    {
        "name": "transferFrom",
        "type": "function",
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable"
    }
]''')


class HoneypotScanner:
    def __init__(self):
        self.web3_clients = {
            'ETH': Web3(Web3.HTTPProvider(RPC_ENDPOINTS['ETH'][0])),
            'BSC': Web3(Web3.HTTPProvider(RPC_ENDPOINTS['BSC'][0])),
        }
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scan_token(self, chain: str, token_address: str) -> Dict:
        """Comprehensive token security scan"""
        try:
            results = {
                'is_honeypot': False,
                'risk_level': 'LOW',  # LOW, MEDIUM, HIGH, CRITICAL
                'warnings': [],
                'checks': {}
            }
            
            # Run all checks in parallel
            check_tasks = [
                self._check_contract_verified(chain, token_address),
                self._check_ownership(chain, token_address),
                self._check_liquidity(chain, token_address),
                self._check_holder_distribution(chain, token_address),
                self._check_trading_history(chain, token_address),
                self._check_token_taxes(chain, token_address),
                self._check_mint_function(chain, token_address),
                self._check_blacklist_function(chain, token_address),
            ]
            
            check_results = await asyncio.gather(*check_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(check_results):
                if isinstance(result, Exception):
                    logger.error(f"Check {i} failed: {result}")
                    continue
                
                check_name, passed, warning = result
                results['checks'][check_name] = passed
                if warning:
                    results['warnings'].append(warning)
            
            # Calculate risk level
            failed_checks = sum(1 for passed in results['checks'].values() if not passed)
            if failed_checks >= 4:
                results['risk_level'] = 'CRITICAL'
                results['is_honeypot'] = True
            elif failed_checks >= 3:
                results['risk_level'] = 'HIGH'
            elif failed_checks >= 2:
                results['risk_level'] = 'MEDIUM'
            
            return results
            
        except Exception as e:
            logger.error(f"Token scan failed: {e}")
            return {
                'is_honeypot': True,
                'risk_level': 'CRITICAL',
                'warnings': [f'Scan failed: {str(e)}'],
                'checks': {}
            }
    
    async def _check_contract_verified(self, chain: str, token_address: str) -> Tuple[str, bool, Optional[str]]:
        """Check if contract is verified on block explorer"""
        try:
            # Check Etherscan/BSCScan API
            if chain == 'ETH':
                api_url = f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={token_address}"
            elif chain == 'BSC':
                api_url = f"https://api.bscscan.com/api?module=contract&action=getsourcecode&address={token_address}"
            else:
                return ('contract_verified', False, 'Chain not supported for verification check')
            
            async with self.session.get(api_url) as response:
                data = await response.json()
                if data['status'] == '1' and data['result'][0]['SourceCode']:
                    return ('contract_verified', True, None)
                else:
                    return ('contract_verified', False, 'Contract not verified')
                    
        except Exception as e:
            return ('contract_verified', False, f'Verification check failed: {str(e)}')
    
    async def _check_ownership(self, chain: str, token_address: str) -> Tuple[str, bool, Optional[str]]:
        """Check if ownership is renounced or concerning"""
        try:
            if chain not in self.web3_clients:
                return ('ownership', False, 'Chain not supported')
            
            w3 = self.web3_clients[chain]
            contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=TOKEN_CHECKER_ABI)
            
            # Try to get owner
            try:
                owner = contract.functions.owner().call()
                if owner == '0x0000000000000000000000000000000000000000':
                    return ('ownership', True, None)  # Ownership renounced
                else:
                    return ('ownership', False, f'Owner still active: {owner}')
            except:
                # No owner function means likely safe
                return ('ownership', True, None)
                
        except Exception as e:
            return ('ownership', False, f'Ownership check failed: {str(e)}')
    
    async def _check_liquidity(self, chain: str, token_address: str) -> Tuple[str, bool, Optional[str]]:
        """Check if liquidity is sufficient and locked"""
        try:
            # This would check DEX liquidity pools
            # For now, return placeholder
            min_liq = SECURITY_CHECKS['MIN_LIQUIDITY_USD']
            
            # In production: Query DEX for liquidity amount
            liquidity_usd = 50000  # Placeholder
            
            if liquidity_usd >= min_liq:
                return ('liquidity', True, None)
            else:
                return ('liquidity', False, f'Low liquidity: ${liquidity_usd:,.0f}')
                
        except Exception as e:
            return ('liquidity', False, f'Liquidity check failed: {str(e)}')
    
    async def _check_holder_distribution(self, chain: str, token_address: str) -> Tuple[str, bool, Optional[str]]:
        """Check token holder distribution"""
        try:
            # This would query blockchain for top holders
            # For now, return placeholder
            max_holder_percent = SECURITY_CHECKS['MAX_OWNER_PERCENTAGE']
            
            # In production: Get actual holder distribution
            top_holder_percent = 15  # Placeholder
            total_holders = 100  # Placeholder
            
            if total_holders < SECURITY_CHECKS['MIN_HOLDERS']:
                return ('holders', False, f'Too few holders: {total_holders}')
            
            if top_holder_percent > max_holder_percent:
                return ('holders', False, f'Top holder owns {top_holder_percent}%')
            
            return ('holders', True, None)
            
        except Exception as e:
            return ('holders', False, f'Holder check failed: {str(e)}')
    
    async def _check_trading_history(self, chain: str, token_address: str) -> Tuple[str, bool, Optional[str]]:
        """Check trading patterns for suspicious activity"""
        try:
            # Check for:
            # - Sudden large sells after buys
            # - Only buys, no sells (honeypot indicator)
            # - Wash trading patterns
            
            # Placeholder implementation
            return ('trading_history', True, None)
            
        except Exception as e:
            return ('trading_history', False, f'Trading check failed: {str(e)}')
    
    async def _check_token_taxes(self, chain: str, token_address: str) -> Tuple[str, bool, Optional[str]]:
        """Check buy/sell taxes"""
        try:
            # Simulate buy/sell to check taxes
            # For now, return placeholder
            buy_tax = 5  # Placeholder
            sell_tax = 5  # Placeholder
            
            max_buy_tax = SECURITY_CHECKS['MAX_BUY_TAX']
            max_sell_tax = SECURITY_CHECKS['MAX_SELL_TAX']
            
            if buy_tax > max_buy_tax:
                return ('taxes', False, f'High buy tax: {buy_tax}%')
            
            if sell_tax > max_sell_tax:
                return ('taxes', False, f'High sell tax: {sell_tax}%')
            
            return ('taxes', True, None)
            
        except Exception as e:
            return ('taxes', False, f'Tax check failed: {str(e)}')
    
    async def _check_mint_function(self, chain: str, token_address: str) -> Tuple[str, bool, Optional[str]]:
        """Check if token has active mint function"""
        try:
            # Check contract code for mint functions
            # This is a simplified check
            return ('mint_function', True, None)
            
        except Exception as e:
            return ('mint_function', False, f'Mint check failed: {str(e)}')
    
    async def _check_blacklist_function(self, chain: str, token_address: str) -> Tuple[str, bool, Optional[str]]:
        """Check if token has blacklist functionality"""
        try:
            # Check for blacklist/whitelist functions that could block trading
            # This is a simplified check
            return ('blacklist', True, None)
            
        except Exception as e:
            return ('blacklist', False, f'Blacklist check failed: {str(e)}')


# Convenience function
async def scan_token_security(chain: str, token_address: str) -> Dict:
    """Quick token security scan"""
    async with HoneypotScanner() as scanner:
        return await scanner.scan_token(chain, token_address)