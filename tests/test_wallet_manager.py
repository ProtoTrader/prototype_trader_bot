"""
Unit tests for wallet manager
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
import base58

from wallet_manager import WalletManager


class TestWalletManager:
    
    @pytest.fixture
    def wallet_manager(self):
        """Create wallet manager instance for testing"""
        # Use temporary file for encryption key
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        
        manager = WalletManager()
        manager._encryption_key_file = tmp_path
        yield manager
        
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    
    def test_create_eth_wallet(self, wallet_manager):
        """Test Ethereum wallet creation"""
        wallet = wallet_manager.create_wallet('ETH')
        
        assert wallet['chain'] == 'ETH'
        assert wallet['address'].startswith('0x')
        assert len(wallet['address']) == 42
        assert wallet['private_key'].startswith('0x')
        assert len(wallet['private_key']) == 66
    
    def test_create_sol_wallet(self, wallet_manager):
        """Test Solana wallet creation"""
        wallet = wallet_manager.create_wallet('SOL')
        
        assert wallet['chain'] == 'SOL'
        assert len(wallet['address']) >= 32
        assert len(wallet['address']) <= 44
        # Verify base58 encoding
        try:
            base58.b58decode(wallet['private_key'])
            assert True
        except:
            assert False, "Invalid base58 private key"
    
    def test_create_trx_wallet(self, wallet_manager):
        """Test Tron wallet creation"""
        wallet = wallet_manager.create_wallet('TRX')
        
        assert wallet['chain'] == 'TRX'
        assert wallet['address'].startswith('T')
        assert len(wallet['address']) == 34
        assert len(wallet['private_key']) == 64  # Hex without 0x
    
    def test_unsupported_chain(self, wallet_manager):
        """Test creating wallet for unsupported chain"""
        with pytest.raises(ValueError, match="Unsupported chain"):
            wallet_manager.create_wallet('BTC')
    
    def test_encrypt_decrypt_private_key(self, wallet_manager):
        """Test private key encryption and decryption"""
        original_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        encrypted = wallet_manager.encrypt_private_key(original_key)
        assert encrypted != original_key
        assert isinstance(encrypted, str)
        
        decrypted = wallet_manager.decrypt_private_key(encrypted)
        assert decrypted == original_key
    
    def test_import_eth_wallet(self, wallet_manager):
        """Test importing Ethereum wallet from private key"""
        # Use a test private key (DO NOT USE IN PRODUCTION)
        private_key = "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        wallet = wallet_manager.import_wallet('ETH', private_key)
        
        assert wallet is not None
        assert wallet['chain'] == 'ETH'
        assert wallet['address'].startswith('0x')
        assert wallet['private_key'] == private_key
    
    def test_import_invalid_wallet(self, wallet_manager):
        """Test importing wallet with invalid private key"""
        wallet = wallet_manager.import_wallet('ETH', 'invalid_key')
        assert wallet is None
    
    def test_validate_eth_address(self, wallet_manager):
        """Test Ethereum address validation"""
        # Valid addresses
        assert wallet_manager.validate_address('ETH', '0x742d35Cc6634C0532925a3b844Bc9e7595f00000')
        assert wallet_manager.validate_address('ETH', '0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe')
        
        # Invalid addresses
        assert not wallet_manager.validate_address('ETH', '0x742d35Cc6634C0532925a3b844Bc9e7595f')  # Too short
        assert not wallet_manager.validate_address('ETH', '742d35Cc6634C0532925a3b844Bc9e7595f00000')  # No 0x
        assert not wallet_manager.validate_address('ETH', '0xGGGG35Cc6634C0532925a3b844Bc9e7595f00000')  # Invalid hex
    
    def test_validate_sol_address(self, wallet_manager):
        """Test Solana address validation"""
        # Valid address
        assert wallet_manager.validate_address('SOL', '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM')
        
        # Invalid addresses
        assert not wallet_manager.validate_address('SOL', 'invalid')
        assert not wallet_manager.validate_address('SOL', '9WzDX')  # Too short
    
    def test_validate_trx_address(self, wallet_manager):
        """Test Tron address validation"""
        # Valid address
        assert wallet_manager.validate_address('TRX', 'TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW')
        
        # Invalid addresses
        assert not wallet_manager.validate_address('TRX', 'XJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW')  # Wrong prefix
        assert not wallet_manager.validate_address('TRX', 'TJCnKsPa7y5o')  # Too short
    
    @patch('wallet_manager.Web3')
    def test_get_balance_mock(self, mock_web3, wallet_manager):
        """Test balance retrieval (mocked)"""
        balance = wallet_manager.get_balance('ETH', '0x742d35Cc6634C0532925a3b844Bc9e7595f00000')
        
        assert balance['chain'] == 'ETH'
        assert balance['address'] == '0x742d35Cc6634C0532925a3b844Bc9e7595f00000'
        assert 'balance' in balance
        assert balance['balance'] == 0.0  # Mock returns 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])