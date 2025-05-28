"""
Chart Commands - Telegram handlers for price charts
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes
from charts.price_charts import PriceChartGenerator
from trading_engine import trading_engine
import logging

logger = logging.getLogger(__name__)


async def show_price_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show price chart for a token"""
    query = update.callback_query
    await query.answer()
    
    # Extract data from callback
    data_parts = query.data.split('_')
    chain = data_parts[2]
    timeframe = data_parts[3] if len(data_parts) > 3 else '24h'
    
    # Get current trade from context
    user_id = query.from_user.id
    trades = trading_engine.get_active_trades(user_id)
    current_index = context.user_data.get('current_trade_index', 0)
    
    if current_index >= len(trades):
        await query.edit_message_text("No active trade found.")
        return
    
    trade = trades[current_index]
    token_address = trade['token_address']
    
    # Send loading message
    await query.edit_message_text("📊 Generating chart...")
    
    try:
        # Generate chart
        async with PriceChartGenerator() as generator:
            chart_bytes = await generator.generate_price_chart(
                token_address, chain, timeframe
            )
        
        if chart_bytes:
            # Send chart
            await query.message.reply_photo(
                photo=InputFile(chart_bytes, filename='price_chart.png'),
                caption=f"📊 {chain} Token Price Chart - {timeframe}\n"
                        f"Token: `{token_address[:8]}...`",
                parse_mode="Markdown",
                reply_markup=get_chart_keyboard(chain)
            )
            
            # Delete the loading message
            await query.message.delete()
        else:
            await query.edit_message_text(
                "❌ Failed to generate chart.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="monitor_refresh")
                ]])
            )
            
    except Exception as e:
        logger.error(f"Error showing price chart: {e}")
        await query.edit_message_text(
            "❌ Error generating chart.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="monitor_refresh")
            ]])
        )


async def show_portfolio_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show portfolio performance chart"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Send loading message
    await query.edit_message_text("📊 Generating portfolio chart...")
    
    try:
        # Get all user trades
        trades = trading_engine.get_active_trades(user_id)
        
        # Generate chart
        async with PriceChartGenerator() as generator:
            chart_bytes = await generator.generate_portfolio_chart(trades)
        
        if chart_bytes:
            # Send chart
            await query.message.reply_photo(
                photo=InputFile(chart_bytes, filename='portfolio_chart.png'),
                caption="📊 Your Portfolio Performance",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Main Menu", callback_data="main")
                ]])
            )
            
            # Delete the loading message
            await query.message.delete()
        else:
            await query.edit_message_text(
                "❌ No trades to display.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Main Menu", callback_data="main")
                ]])
            )
            
    except Exception as e:
        logger.error(f"Error showing portfolio chart: {e}")
        await query.edit_message_text("❌ Error generating chart.")


def get_chart_keyboard(chain: str) -> InlineKeyboardMarkup:
    """Get keyboard for chart timeframe selection"""
    keyboard = [
        [
            InlineKeyboardButton("1H", callback_data=f"show_chart_{chain}_1h"),
            InlineKeyboardButton("24H", callback_data=f"show_chart_{chain}_24h"),
            InlineKeyboardButton("7D", callback_data=f"show_chart_{chain}_7d"),
            InlineKeyboardButton("30D", callback_data=f"show_chart_{chain}_30d"),
        ],
        [
            InlineKeyboardButton("🔙 Back to Monitor", callback_data="monitor_refresh")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)