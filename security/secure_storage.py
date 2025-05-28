"""
Secure Storage - Advanced encryption and key management
"""

import os
import json
import base64
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import keyring
import logging
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class SecureStorage:
    """Secure storage for sensitive data like private keys"""
    
    def __init__(self, storage_file: str = ".secure_storage"):
        self.storage_file = storage_file
        self.master_key = None
        self.cipher = None
        self.session_keys = {}  # Temporary decrypted keys with expiration
        
        # Initialize master encryption
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption with master key"""
        try:
            # Try to get master key from system keyring
            master_key = keyring.get_password("ProtoTraderBot", "master_key")
            
            if not master_key:
                # Generate new master key
                master_key = Fernet.generate_key().decode()
                keyring.set_password("ProtoTraderBot", "master_key", master_key)
                logger.info("Generated new master encryption key")
            
            self.master_key = master_key.encode()
            self.cipher = Fernet(self.master_key)
            
        except Exception as e:
            logger.error(f"Failed to initialize keyring, using file-based encryption: {e}")
            # Fallback to file-based encryption
            self._initialize_file_encryption()
    
    def _initialize_file_encryption(self):
        """Fallback file-based encryption"""
        key_file = ".encryption_key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self.master_key = f.read()
        else:
            self.master_key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(self.master_key)
            os.chmod(key_file, 0o600)  # Read/write for owner only
        
        self.cipher = Fernet(self.master_key)
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def store_private_key(self, user_id: int, chain: str, address: str, 
                         private_key: str, password: Optional[str] = None) -> bool:
        """Store private key with multiple layers of encryption"""
        try:
            # Load existing storage
            storage = self._load_storage()
            
            # Create user storage if not exists
            user_key = str(user_id)
            if user_key not in storage:
                storage[user_key] = {
                    'wallets': {},
                    'created_at': datetime.now().isoformat()
                }
            
            # Generate unique salt for this key
            salt = os.urandom(16)
            
            # Double encryption
            # Layer 1: User password (if provided)
            if password:
                user_cipher = Fernet(self._derive_key(password, salt))
                encrypted_layer1 = user_cipher.encrypt(private_key.encode())
            else:
                encrypted_layer1 = private_key.encode()
            
            # Layer 2: Master key encryption
            encrypted_layer2 = self.cipher.encrypt(encrypted_layer1)
            
            # Create wallet entry
            wallet_id = f"{chain}_{address}"
            wallet_data = {
                'chain': chain,
                'address': address,
                'encrypted_key': base64.b64encode(encrypted_layer2).decode(),
                'salt': base64.b64encode(salt).decode() if password else None,
                'password_protected': bool(password),
                'created_at': datetime.now().isoformat(),
                'last_accessed': None,
                'access_count': 0
            }
            
            # Store
            storage[user_key]['wallets'][wallet_id] = wallet_data
            
            # Save storage
            self._save_storage(storage)
            
            logger.info(f"Stored private key for user {user_id}, wallet {wallet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store private key: {e}")
            return False
    
    def retrieve_private_key(self, user_id: int, chain: str, address: str,
                           password: Optional[str] = None, 
                           cache_duration: int = 300) -> Optional[str]:
        """Retrieve private key with optional caching"""
        try:
            # Check session cache first
            cache_key = f"{user_id}_{chain}_{address}"
            if cache_key in self.session_keys:
                cached = self.session_keys[cache_key]
                if datetime.now() < cached['expires']:
                    logger.debug("Retrieved key from session cache")
                    return cached['key']
                else:
                    del self.session_keys[cache_key]
            
            # Load from storage
            storage = self._load_storage()
            user_key = str(user_id)
            
            if user_key not in storage:
                return None
            
            wallet_id = f"{chain}_{address}"
            if wallet_id not in storage[user_key]['wallets']:
                return None
            
            wallet_data = storage[user_key]['wallets'][wallet_id]
            
            # Decrypt
            encrypted_data = base64.b64decode(wallet_data['encrypted_key'])
            
            # Layer 2: Master key decryption
            decrypted_layer1 = self.cipher.decrypt(encrypted_data)
            
            # Layer 1: User password decryption (if needed)
            if wallet_data['password_protected']:
                if not password:
                    logger.warning(f"Password required for wallet {wallet_id}")
                    return None
                
                salt = base64.b64decode(wallet_data['salt'])
                user_cipher = Fernet(self._derive_key(password, salt))
                
                try:
                    private_key = user_cipher.decrypt(decrypted_layer1).decode()
                except:
                    logger.warning(f"Invalid password for wallet {wallet_id}")
                    return None
            else:
                private_key = decrypted_layer1.decode()
            
            # Update access info
            wallet_data['last_accessed'] = datetime.now().isoformat()
            wallet_data['access_count'] += 1
            self._save_storage(storage)
            
            # Cache in session
            if cache_duration > 0:
                self.session_keys[cache_key] = {
                    'key': private_key,
                    'expires': datetime.now() + timedelta(seconds=cache_duration)
                }
            
            logger.info(f"Retrieved private key for wallet {wallet_id}")
            return private_key
            
        except Exception as e:
            logger.error(f"Failed to retrieve private key: {e}")
            return None
    
    def delete_private_key(self, user_id: int, chain: str, address: str) -> bool:
        """Delete a stored private key"""
        try:
            storage = self._load_storage()
            user_key = str(user_id)
            
            if user_key in storage:
                wallet_id = f"{chain}_{address}"
                if wallet_id in storage[user_key]['wallets']:
                    del storage[user_key]['wallets'][wallet_id]
                    self._save_storage(storage)
                    
                    # Clear from cache
                    cache_key = f"{user_id}_{chain}_{address}"
                    if cache_key in self.session_keys:
                        del self.session_keys[cache_key]
                    
                    logger.info(f"Deleted private key for wallet {wallet_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete private key: {e}")
            return False
    
    def list_user_wallets(self, user_id: int) -> Dict[str, Dict]:
        """List all wallets for a user (without private keys)"""
        try:
            storage = self._load_storage()
            user_key = str(user_id)
            
            if user_key not in storage:
                return {}
            
            wallets = {}
            for wallet_id, wallet_data in storage[user_key]['wallets'].items():
                wallets[wallet_id] = {
                    'chain': wallet_data['chain'],
                    'address': wallet_data['address'],
                    'password_protected': wallet_data['password_protected'],
                    'created_at': wallet_data['created_at'],
                    'last_accessed': wallet_data['last_accessed'],
                    'access_count': wallet_data['access_count']
                }
            
            return wallets
            
        except Exception as e:
            logger.error(f"Failed to list wallets: {e}")
            return {}
    
    def export_encrypted_backup(self, user_id: int, backup_password: str) -> Optional[str]:
        """Export encrypted backup of user's keys"""
        try:
            storage = self._load_storage()
            user_key = str(user_id)
            
            if user_key not in storage:
                return None
            
            # Create backup data
            backup_data = {
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'wallets': storage[user_key]['wallets']
            }
            
            # Encrypt backup with password
            salt = os.urandom(16)
            backup_cipher = Fernet(self._derive_key(backup_password, salt))
            
            backup_json = json.dumps(backup_data)
            encrypted_backup = backup_cipher.encrypt(backup_json.encode())
            
            # Create final backup format
            final_backup = {
                'version': '1.0',
                'salt': base64.b64encode(salt).decode(),
                'data': base64.b64encode(encrypted_backup).decode(),
                'checksum': hashlib.sha256(encrypted_backup).hexdigest()
            }
            
            return base64.b64encode(json.dumps(final_backup).encode()).decode()
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def import_encrypted_backup(self, backup_data: str, backup_password: str) -> bool:
        """Import encrypted backup"""
        try:
            # Decode backup
            backup_json = json.loads(base64.b64decode(backup_data))
            
            # Verify checksum
            encrypted_data = base64.b64decode(backup_json['data'])
            if hashlib.sha256(encrypted_data).hexdigest() != backup_json['checksum']:
                logger.error("Backup checksum mismatch")
                return False
            
            # Decrypt backup
            salt = base64.b64decode(backup_json['salt'])
            backup_cipher = Fernet(self._derive_key(backup_password, salt))
            
            try:
                decrypted_json = backup_cipher.decrypt(encrypted_data).decode()
                backup_data = json.loads(decrypted_json)
            except:
                logger.error("Invalid backup password")
                return False
            
            # Import wallets
            user_id = backup_data['user_id']
            storage = self._load_storage()
            user_key = str(user_id)
            
            if user_key not in storage:
                storage[user_key] = {
                    'wallets': {},
                    'created_at': datetime.now().isoformat()
                }
            
            # Merge wallets
            storage[user_key]['wallets'].update(backup_data['wallets'])
            self._save_storage(storage)
            
            logger.info(f"Imported backup for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import backup: {e}")
            return False
    
    def _load_storage(self) -> Dict:
        """Load encrypted storage file"""
        if not os.path.exists(self.storage_file):
            return {}
        
        try:
            with open(self.storage_file, 'rb') as f:
                encrypted_data = f.read()
                decrypted_data = self.cipher.decrypt(encrypted_data)
                return json.loads(decrypted_data)
        except:
            return {}
    
    def _save_storage(self, storage: Dict):
        """Save encrypted storage file"""
        try:
            encrypted_data = self.cipher.encrypt(json.dumps(storage).encode())
            
            # Write to temporary file first
            temp_file = f"{self.storage_file}.tmp"
            with open(temp_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Atomic rename
            os.rename(temp_file, self.storage_file)
            os.chmod(self.storage_file, 0o600)  # Read/write for owner only
            
        except Exception as e:
            logger.error(f"Failed to save storage: {e}")
            raise
    
    def clear_session_cache(self):
        """Clear all cached keys from memory"""
        self.session_keys.clear()
        logger.info("Cleared session key cache")


# Singleton instance
secure_storage = SecureStorage()