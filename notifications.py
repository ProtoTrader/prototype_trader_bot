"""
Notifications Module - Advanced notification system
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from user_data import user_data
import os

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self):
        self.bot = None
        self.active_alerts = {}
        self.notification_queue = asyncio.Queue()
        self.worker_task = None
        
    async def initialize(self, bot_token: str):
        """Initialize the notification manager with bot"""
        self.bot = Bot(token=bot_token)
        self.worker_task = asyncio.create_task(self._notification_worker())
        logger.info("Notification manager initialized")
    
    async def shutdown(self):
        """Shutdown notification manager"""
        if self.worker_task:
            self.worker_task.cancel()
            await asyncio.gather(self.worker_task, return_exceptions=True)
    
    async def _notification_worker(self):
        """Process notifications from queue"""
        while True:
            try:
                notification = await self.notification_queue.get()
                await self._send_notification(notification)
                await asyncio.sleep(0.5)  # Rate limiting
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification worker: {e}")
    
    async def _send_notification(self, notification: Dict):
        """Send individual notification"""
        try:
            user_id = notification['user_id']
            message = notification['message']
            reply_markup = notification.get('reply_markup')
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except TelegramError as e:
            logger.error(f"Failed to send notification to {user_id}: {e}")
    
    async def notify_trade_executed(self, user_id: int, trade_info: Dict):
        """Notify user about executed trade"""
        trade_type = trade_info['type'].upper()
        chain = trade_info['chain']
        amount = trade_info['amount']
        tx_hash = trade_info.get('tx_hash', 'N/A')
        
        message = f"🔔 **Trade Executed**\n\n"
        message += f"Type: **{trade_type}**\n"
        message += f"Chain: **{chain}**\n"
        message += f"Amount: **{amount}**\n"
        message += f"Tx: `{tx_hash[:16]}...`\n"
        
        keyboard = [[
            InlineKeyboardButton("📊 View Trade", callback_data="monitor_refresh"),
            InlineKeyboardButton("❌ Close", callback_data="delete_message")
        ]]
        
        await self.notification_queue.put({
            'user_id': user_id,
            'message': message,
            'reply_markup': InlineKeyboardMarkup(keyboard)
        })
    
    async def notify_copy_trade(self, user_id: int, leader_wallet: str, trade_info: Dict):
        """Notify user about copy trade"""
        message = f"🔄 **Copy Trade Executed**\n\n"
        message += f"Following: `{leader_wallet[:8]}...`\n"
        message += f"Action: **{trade_info['type'].upper()}**\n"
        message += f"Token: `{trade_info['token_address'][:8]}...`\n"
        message += f"Status: {'✅ Success' if trade_info.get('success') else '❌ Failed'}\n"
        
        keyboard = [[
            InlineKeyboardButton("📊 View Details", callback_data="monitor_refresh"),
            InlineKeyboardButton("⚙️ Settings", callback_data="ct")
        ]]
        
        await self.notification_queue.put({
            'user_id': user_id,
            'message': message,
            'reply_markup': InlineKeyboardMarkup(keyboard)
        })
    
    async def notify_price_alert(self, user_id: int, token: str, price: float, 
                               alert_type: str, change_percent: float):
        """Notify user about price alert"""
        emoji = "📈" if alert_type == "above" else "📉"
        
        message = f"{emoji} **Price Alert**\n\n"
        message += f"Token: `{token[:8]}...`\n"
        message += f"Price: **${price:.6f}**\n"
        message += f"Change: **{change_percent:+.2f}%**\n"
        
        keyboard = [[
            InlineKeyboardButton("📊 View Chart", callback_data=f"show_chart_ETH_24h"),
            InlineKeyboardButton("💰 Quick Sell", callback_data=f"quick_sell_50_ETH")
        ]]
        
        await self.notification_queue.put({
            'user_id': user_id,
            'message': message,
            'reply_markup': InlineKeyboardMarkup(keyboard)
        })
    
    async def notify_stop_loss_triggered(self, user_id: int, trade_id: str, loss_percent: float):
        """Notify user about stop loss trigger"""
        message = f"🛑 **Stop Loss Triggered**\n\n"
        message += f"Trade ID: `{trade_id[:8]}...`\n"
        message += f"Loss: **{loss_percent:.2f}%**\n"
        message += f"Action: Automatic sell executed\n"
        
        await self.notification_queue.put({
            'user_id': user_id,
            'message': message
        })
    
    async def notify_take_profit_triggered(self, user_id: int, trade_id: str, profit_percent: float):
        """Notify user about take profit trigger"""
        message = f"🎯 **Take Profit Triggered**\n\n"
        message += f"Trade ID: `{trade_id[:8]}...`\n"
        message += f"Profit: **+{profit_percent:.2f}%**\n"
        message += f"Action: Partial sell executed\n"
        
        await self.notification_queue.put({
            'user_id': user_id,
            'message': message
        })
    
    async def notify_security_warning(self, user_id: int, token: str, warnings: List[str]):
        """Notify user about security issues"""
        message = f"⚠️ **Security Warning**\n\n"
        message += f"Token: `{token[:8]}...`\n"
        message += "Issues detected:\n"
        for warning in warnings[:3]:  # Limit to 3 warnings
            message += f"• {warning}\n"
        
        keyboard = [[
            InlineKeyboardButton("🔍 View Details", callback_data="security_details"),
            InlineKeyboardButton("❌ Cancel Trade", callback_data="cancel_trade")
        ]]
        
        await self.notification_queue.put({
            'user_id': user_id,
            'message': message,
            'reply_markup': InlineKeyboardMarkup(keyboard)
        })
    
    async def send_daily_summary(self, user_id: int):
        """Send daily trading summary"""
        # Get user's trades from last 24h
        # Calculate P&L, success rate, etc.
        
        message = f"📊 **Daily Summary**\n\n"
        message += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        message += f"Trades: 10\n"
        message += f"Success Rate: 80%\n"
        message += f"Total P&L: +$500 (+25%)\n"
        message += f"Best Trade: +$200 (SOL)\n"
        message += f"Worst Trade: -$50 (ETH)\n"
        
        keyboard = [[
            InlineKeyboardButton("📈 View Portfolio", callback_data="portfolio_chart"),
            InlineKeyboardButton("📊 Detailed Report", callback_data="detailed_report")
        ]]
        
        await self.notification_queue.put({
            'user_id': user_id,
            'message': message,
            'reply_markup': InlineKeyboardMarkup(keyboard)
        })
    
    def schedule_price_alert(self, user_id: int, token: str, target_price: float, 
                           alert_type: str = "above"):
        """Schedule a price alert"""
        alert_id = f"{user_id}_{token}_{target_price}_{alert_type}"
        
        self.active_alerts[alert_id] = {
            'user_id': user_id,
            'token': token,
            'target_price': target_price,
            'alert_type': alert_type,
            'created_at': datetime.now()
        }
        
        logger.info(f"Price alert scheduled: {alert_id}")
        return alert_id
    
    def cancel_price_alert(self, alert_id: str):
        """Cancel a price alert"""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            logger.info(f"Price alert cancelled: {alert_id}")


# Singleton instance
notification_manager = NotificationManager()

# Initialize on import if TOKEN is available
TOKEN = os.getenv('TOKEN')
if TOKEN:
    asyncio.create_task(notification_manager.initialize(TOKEN))