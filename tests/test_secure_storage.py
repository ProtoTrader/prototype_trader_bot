"""
Unit tests for secure storage
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

from security.secure_storage import SecureStorage


class TestSecureStorage:
    
    @pytest.fixture
    def secure_storage(self):
        """Create secure storage instance for testing"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            storage = SecureStorage(storage_file=tmp.name)
            yield storage
            # Cleanup
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
            if os.path.exists('.encryption_key'):
                os.remove('.encryption_key')
    
    def test_store_and_retrieve_private_key(self, secure_storage):
        """Test storing and retrieving private key"""
        user_id = 12345
        chain = 'ETH'
        address = '0x742d35Cc6634C0532925a3b844Bc9e7595f00000'
        private_key = '0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'
        
        # Store key
        success = secure_storage.store_private_key(
            user_id, chain, address, private_key
        )
        assert success
        
        # Retrieve key
        retrieved_key = secure_storage.retrieve_private_key(
            user_id, chain, address
        )
        assert retrieved_key == private_key
    
    def test_store_with_password(self, secure_storage):
        """Test storing private key with password protection"""
        user_id = 12345
        chain = 'ETH'
        address = '0x742d35Cc6634C0532925a3b844Bc9e7595f00000'
        private_key = '0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'
        password = 'strong_password_123'
        
        # Store with password
        success = secure_storage.store_private_key(
            user_id, chain, address, private_key, password
        )
        assert success
        
        # Try to retrieve without password - should fail
        retrieved_key = secure_storage.retrieve_private_key(
            user_id, chain, address
        )
        assert retrieved_key is None
        
        # Try with wrong password - should fail
        retrieved_key = secure_storage.retrieve_private_key(
            user_id, chain, address, 'wrong_password'
        )
        assert retrieved_key is None
        
        # Retrieve with correct password
        retrieved_key = secure_storage.retrieve_private_key(
            user_id, chain, address, password
        )
        assert retrieved_key == private_key
    
    def test_session_cache(self, secure_storage):
        """Test session caching of keys"""
        user_id = 12345
        chain = 'ETH'
        address = '0x742d35Cc6634C0532925a3b844Bc9e7595f00000'
        private_key = '0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'
        
        # Store key
        secure_storage.store_private_key(user_id, chain, address, private_key)
        
        # First retrieval - from storage
        key1 = secure_storage.retrieve_private_key(
            user_id, chain, address, cache_duration=300
        )
        assert key1 == private_key
        
        # Check cache
        cache_key = f"{user_id}_{chain}_{address}"
        assert cache_key in secure_storage.session_keys
        
        # Second retrieval - should be from cache
        key2 = secure_storage.retrieve_private_key(
            user_id, chain, address
        )
        assert key2 == private_key
    
    def test_delete_private_key(self, secure_storage):
        """Test deleting private key"""
        user_id = 12345
        chain = 'ETH'
        address = '0x742d35Cc6634C0532925a3b844Bc9e7595f00000'
        private_key = '0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'
        
        # Store key
        secure_storage.store_private_key(user_id, chain, address, private_key)
        
        # Delete key
        success = secure_storage.delete_private_key(user_id, chain, address)
        assert success
        
        # Try to retrieve - should be None
        retrieved_key = secure_storage.retrieve_private_key(
            user_id, chain, address
        )
        assert retrieved_key is None
    
    def test_list_user_wallets(self, secure_storage):
        """Test listing user wallets"""
        user_id = 12345
        
        # Store multiple wallets
        wallets = [
            ('ETH', '0x1111', 'key1'),
            ('ETH', '0x2222', 'key2'),
            ('SOL', 'sol_address', 'key3')
        ]
        
        for chain, address, key in wallets:
            secure_storage.store_private_key(user_id, chain, address, key)
        
        # List wallets
        user_wallets = secure_storage.list_user_wallets(user_id)
        
        assert len(user_wallets) == 3
        assert 'ETH_0x1111' in user_wallets
        assert 'ETH_0x2222' in user_wallets
        assert 'SOL_sol_address' in user_wallets
        
        # Check that private keys are not exposed
        for wallet_id, wallet_info in user_wallets.items():
            assert 'private_key' not in wallet_info
            assert 'encrypted_key' not in wallet_info
    
    def test_export_import_backup(self, secure_storage):
        """Test backup export and import"""
        user_id = 12345
        backup_password = 'backup_pass_123'
        
        # Store some wallets
        wallets = [
            ('ETH', '0x1111', 'key1'),
            ('SOL', 'sol_address', 'key2')
        ]
        
        for chain, address, key in wallets:
            secure_storage.store_private_key(user_id, chain, address, key)
        
        # Export backup
        backup_data = secure_storage.export_encrypted_backup(
            user_id, backup_password
        )
        assert backup_data is not None
        assert isinstance(backup_data, str)
        
        # Clear storage
        secure_storage.storage_file = 'new_storage.tmp'
        secure_storage._save_storage({})
        
        # Import backup
        success = secure_storage.import_encrypted_backup(
            backup_data, backup_password
        )
        assert success
        
        # Verify wallets restored
        restored_wallets = secure_storage.list_user_wallets(user_id)
        assert len(restored_wallets) == 2
        
        # Verify keys can be retrieved
        key1 = secure_storage.retrieve_private_key(user_id, 'ETH', '0x1111')
        assert key1 == 'key1'
        
        # Cleanup
        if os.path.exists('new_storage.tmp'):
            os.remove('new_storage.tmp')
    
    def test_import_backup_wrong_password(self, secure_storage):
        """Test importing backup with wrong password"""
        user_id = 12345
        backup_password = 'backup_pass_123'
        
        # Create and export backup
        secure_storage.store_private_key(user_id, 'ETH', '0x1111', 'key1')
        backup_data = secure_storage.export_encrypted_backup(
            user_id, backup_password
        )
        
        # Try to import with wrong password
        success = secure_storage.import_encrypted_backup(
            backup_data, 'wrong_password'
        )
        assert not success
    
    @patch('keyring.get_password')
    @patch('keyring.set_password')
    def test_keyring_integration(self, mock_set, mock_get, secure_storage):
        """Test system keyring integration"""
        # Test when keyring is available
        mock_get.return_value = None  # No existing key
        
        # This should trigger key generation
        secure_storage._initialize_encryption()
        
        # Verify keyring was called
        mock_set.assert_called_once()
        assert mock_set.call_args[0][0] == "ProtoTraderBot"
        assert mock_set.call_args[0][1] == "master_key"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])