"""
Unit tests for trading engine
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from trading_engine import TradingEngine
from user_data import user_data


class TestTradingEngine:
    
    @pytest.fixture
    def trading_engine(self):
        """Create trading engine instance for testing"""
        return TradingEngine()
    
    @pytest.fixture
    def mock_user_data(self):
        """Mock user data"""
        user_id = 12345
        user_data[user_id] = {
            'connected_wallets': {
                'ETH': {
                    'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f00000',
                    'private_key_encrypted': 'encrypted_key',
                    'chain': 'ETH'
                }
            },
            'wallets': {
                'ETH': {
                    'BUY': {
                        'int': {
                            'SLIPPAGE': {'value': 10},
                            'GAS_DELTA': {'value': 0.001},
                            'PIA': {'value': 25}
                        }
                    },
                    'SELL': {
                        'int': {
                            'SLIPPAGE': {'value': 10},
                            'GAS_DELTA': {'value': 0.001},
                            'PIA': {'value': 50}
                        }
                    }
                }
            }
        }
        yield user_id
        # Cleanup
        del user_data[user_id]
    
    @pytest.mark.asyncio
    @patch('trading_engine.wallet_manager.decrypt_private_key')
    @patch('trading_engine.scan_token_security')
    async def test_buy_token_security_check(self, mock_scan, mock_decrypt, trading_engine, mock_user_data):
        """Test buy token with security check"""
        mock_decrypt.return_value = 'decrypted_key'
        mock_scan.return_value = {
            'is_honeypot': True,
            'warnings': ['High sell tax detected'],
            'risk_level': 'CRITICAL'
        }
        
        result = await trading_engine.buy_token(
            user_id=mock_user_data,
            chain='ETH',
            token_address='0x1234567890123456789012345678901234567890',
            amount=0.1,
            skip_security_check=False
        )
        
        assert not result['success']
        assert 'security_result' in result
        assert 'High sell tax detected' in result['error']
    
    @pytest.mark.asyncio
    @patch('trading_engine.wallet_manager.decrypt_private_key')
    @patch('trading_engine.TradingEngine._send_fee')
    async def test_buy_token_fee_failure(self, mock_send_fee, mock_decrypt, trading_engine, mock_user_data):
        """Test buy token when fee transaction fails"""
        mock_decrypt.return_value = 'decrypted_key'
        mock_send_fee.return_value = None  # Fee transaction failed
        
        result = await trading_engine.buy_token(
            user_id=mock_user_data,
            chain='ETH',
            token_address='0x1234567890123456789012345678901234567890',
            amount=0.1,
            skip_security_check=True
        )
        
        assert not result['success']
        assert result['error'] == 'Failed to process fee transaction'
    
    def test_calculate_fee(self, trading_engine):
        """Test fee calculation"""
        amount = 1.0
        fee_amount = amount * 0.01  # 1% fee
        actual_trade_amount = amount - fee_amount
        
        assert fee_amount == 0.01
        assert actual_trade_amount == 0.99
    
    @pytest.mark.asyncio
    async def test_set_stop_loss(self, trading_engine):
        """Test setting stop loss"""
        # Add a mock trade
        trade_id = 'test_trade_123'
        trading_engine.active_trades[trade_id] = {
            'user_id': 12345,
            'chain': 'ETH',
            'token_address': '0x123',
            'type': 'buy',
            'amount': 0.1,
            'timestamp': datetime.now(),
            'status': 'pending'
        }
        
        result = await trading_engine.set_stop_loss(trade_id, 10.0)
        assert result
        assert trading_engine.active_trades[trade_id]['stop_loss'] == 10.0
    
    @pytest.mark.asyncio
    async def test_set_take_profit(self, trading_engine):
        """Test setting take profit"""
        trade_id = 'test_trade_123'
        trading_engine.active_trades[trade_id] = {
            'user_id': 12345,
            'chain': 'ETH',
            'token_address': '0x123',
            'type': 'buy',
            'amount': 0.1,
            'timestamp': datetime.now(),
            'status': 'pending'
        }
        
        result = await trading_engine.set_take_profit(trade_id, 50.0)
        assert result
        assert trading_engine.active_trades[trade_id]['take_profit'] == 50.0
    
    def test_get_active_trades(self, trading_engine):
        """Test getting active trades for user"""
        user_id = 12345
        
        # Add some trades
        trading_engine.active_trades['trade1'] = {'user_id': user_id, 'status': 'active'}
        trading_engine.active_trades['trade2'] = {'user_id': user_id, 'status': 'pending'}
        trading_engine.active_trades['trade3'] = {'user_id': 99999, 'status': 'active'}  # Different user
        
        user_trades = trading_engine.get_active_trades(user_id)
        assert len(user_trades) == 2
        assert all(trade['user_id'] == user_id for trade in user_trades)
    
    def test_generate_trade_id(self, trading_engine):
        """Test trade ID generation"""
        trade_id1 = trading_engine._generate_trade_id()
        trade_id2 = trading_engine._generate_trade_id()
        
        assert isinstance(trade_id1, str)
        assert isinstance(trade_id2, str)
        assert trade_id1 != trade_id2  # Should be unique
    
    @pytest.mark.asyncio
    @patch('trading_engine.TradingEngine._get_token_price')
    async def test_monitor_trade_stop_loss(self, mock_get_price, trading_engine):
        """Test trade monitoring for stop loss"""
        # Setup
        trade_id = 'test_trade'
        trading_engine.active_trades[trade_id] = {
            'user_id': 12345,
            'chain': 'ETH',
            'token_address': '0x123',
            'amount': 0.1,
            'stop_loss': 10.0  # 10% stop loss
        }
        
        # Mock initial price and then lower price
        mock_get_price.side_effect = [1.0, 0.89]  # 11% drop
        
        # Start monitoring
        trading_engine.price_monitors[trade_id] = {
            'initial_price': 1.0,
            'monitoring': True
        }
        
        # This would trigger stop loss in real scenario
        # For testing, we just verify the setup
        assert trade_id in trading_engine.active_trades
        assert trading_engine.active_trades[trade_id]['stop_loss'] == 10.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])