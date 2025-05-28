"""
Wallet Manager - Handles crypto wallet creation and management
"""

import os
import json
from typing import Dict, Optional, Tuple
from eth_account import Account
from solana.keypair import Keypair
from tronpy import Tron
from tronpy.keys import PrivateKey
import base58
from cryptography.fernet import Fernet


class WalletManager:
    """Manages cryptocurrency wallets for multiple chains"""
    
    def __init__(self):
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for wallet private keys"""
        key_file = '.wallet_key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def create_wallet(self, chain: str) -> Dict[str, str]:
        """Create a new wallet for the specified chain"""
        if chain == 'ETH':
            return self._create_eth_wallet()
        elif chain == 'SOL':
            return self._create_sol_wallet()
        elif chain == 'TRX':
            return self._create_trx_wallet()
        else:
            raise ValueError(f"Unsupported chain: {chain}")
    
    def _create_eth_wallet(self) -> Dict[str, str]:
        """Create Ethereum wallet"""
        account = Account.create()
        return {
            'address': account.address,
            'private_key': account.key.hex(),
            'chain': 'ETH'
        }
    
    def _create_sol_wallet(self) -> Dict[str, str]:
        """Create Solana wallet"""
        keypair = Keypair()
        return {
            'address': str(keypair.pubkey()),
            'private_key': base58.b58encode(keypair.secret()).decode('utf-8'),
            'chain': 'SOL'
        }
    
    def _create_trx_wallet(self) -> Dict[str, str]:
        """Create Tron wallet"""
        private_key = PrivateKey.random()
        address = private_key.public_key.to_base58check_address()
        return {
            'address': address,
            'private_key': private_key.hex(),
            'chain': 'TRX'
        }
    
    def encrypt_private_key(self, private_key: str) -> str:
        """Encrypt private key for storage"""
        return self.cipher.encrypt(private_key.encode()).decode()
    
    def decrypt_private_key(self, encrypted_key: str) -> str:
        """Decrypt private key for use"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()
    
    def import_wallet(self, chain: str, private_key: str) -> Optional[Dict[str, str]]:
        """Import existing wallet from private key"""
        try:
            if chain == 'ETH':
                account = Account.from_key(private_key)
                return {
                    'address': account.address,
                    'private_key': private_key,
                    'chain': 'ETH'
                }
            elif chain == 'SOL':
                # Decode base58 private key
                secret = base58.b58decode(private_key)
                keypair = Keypair.from_seed(secret[:32])
                return {
                    'address': str(keypair.pubkey()),
                    'private_key': private_key,
                    'chain': 'SOL'
                }
            elif chain == 'TRX':
                private_key_obj = PrivateKey(bytes.fromhex(private_key))
                address = private_key_obj.public_key.to_base58check_address()
                return {
                    'address': address,
                    'private_key': private_key,
                    'chain': 'TRX'
                }
        except Exception as e:
            print(f"Error importing wallet: {e}")
            return None
    
    def validate_address(self, chain: str, address: str) -> bool:
        """Validate wallet address for the specified chain"""
        try:
            if chain == 'ETH':
                # Basic Ethereum address validation
                if address.startswith('0x') and len(address) == 42:
                    int(address, 16)
                    return True
            elif chain == 'SOL':
                # Basic Solana address validation
                decoded = base58.b58decode(address)
                return len(decoded) == 32
            elif chain == 'TRX':
                # Basic Tron address validation
                if address.startswith('T') and len(address) == 34:
                    base58.b58decode(address)
                    return True
        except:
            pass
        return False
    
    def get_balance(self, chain: str, address: str) -> Dict[str, float]:
        """Get wallet balance (placeholder - needs RPC implementation)"""
        # This would connect to blockchain nodes to get actual balances
        # For now, return mock data
        return {
            'balance': 0.0,
            'chain': chain,
            'address': address
        }


# Singleton instance
wallet_manager = WalletManager()