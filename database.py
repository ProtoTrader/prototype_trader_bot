"""
Database module - Handles data persistence
"""

import json
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class Database:
    """Simple JSON-based database for user data persistence"""
    
    def __init__(self, filename: str = "user_data.json"):
        self.filename = filename
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading database: {e}")
                return {}
        return {}
    
    def save_data(self, data: Dict[str, Any]) -> bool:
        """Save data to JSON file"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            return False
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user data"""
        return self.data.get(str(user_id), {})
    
    def save_user(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Save user data"""
        self.data[str(user_id)] = user_data
        return self.save_data(self.data)
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user data"""
        if str(user_id) in self.data:
            del self.data[str(user_id)]
            return self.save_data(self.data)
        return False


# Singleton instance
db = Database()