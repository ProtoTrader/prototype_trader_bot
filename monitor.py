from telegram.ext import (Application,
                          CommandHandler,
                          CallbackQueryHandler,
                          ConversationHandler,
                          MessageHandler,
                          ContextTypes,
                          filters
                          )
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from button import button_bot_name
from user_data import user_data
from trading_engine import trading_engine
from datetime import datetime, timedelta


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    # Get active trades for the user
    trades = trading_engine.get_active_trades(user_id)
    
    if not trades:
        message = "📊 **Trade Monitor**\n\n"
        message += "No active trades.\n\n"
        message += "Start trading from your wallet menu!"
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main")]]
        await update.message.reply_text(message, parse_mode="Markdown", 
                                        reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        # Show first trade by default
        context.user_data['current_trade_index'] = 0
        await show_trade_monitor(update, context, trades[0])

async def show_trade_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE, trade: dict) -> None:
    """Display trade monitor for a specific trade"""
    user_id = update.effective_user.id
    trades = trading_engine.get_active_trades(user_id)
    current_index = context.user_data.get('current_trade_index', 0)
    
    # Calculate time elapsed
    time_elapsed = datetime.now() - trade['timestamp']
    hours, remainder = divmod(time_elapsed.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Build message
    message = f"📊 **Trade Monitor** ({current_index + 1}/{len(trades)})\n\n"
    message += f"🪙 Token: `{trade['token_address'][:8]}...`\n"
    message += f"⛓️ Chain: **{trade['chain']}**\n"
    message += f"📈 Type: **{trade['type'].upper()}**\n"
    message += f"💰 Amount: **{trade['amount']} {trade['chain']}**\n"
    message += f"⏱️ Time elapsed: {hours}h {minutes}m {seconds}s\n\n"
    
    # Add stop loss / take profit info if set
    if 'stop_loss' in trade:
        message += f"🛑 Stop Loss: **-{trade['stop_loss']}%**\n"
    if 'take_profit' in trade:
        message += f"🎯 Take Profit: **+{trade['take_profit']}%**\n"
    
    message += f"\n🔗 Tx: `{trade['tx_hash'][:16]}...`\n"
    message += f"📊 Status: **{trade['status']}**"
    
    keyboard = monitor_keyboard(user_id, trade['chain'], current_index, len(trades))
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message, parse_mode="Markdown", 
                                                      reply_markup=keyboard)
    else:
        await update.message.reply_text(message, parse_mode="Markdown", 
                                        reply_markup=keyboard)

def monitor_keyboard(user_id: int, crypto: str, current_index: int, total_trades: int) -> InlineKeyboardMarkup:
    keyboard = [
        button_bot_name(),
    ]
    
    # Navigation buttons if multiple trades
    if total_trades > 1:
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data="monitor_prev"))
        nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="monitor_refresh"))
        if current_index < total_trades - 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data="monitor_next"))
        keyboard.append(nav_buttons)
    else:
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="monitor_refresh")])
    
    # Trade actions
    keyboard.append([
        InlineKeyboardButton("💰 Sell 25%", callback_data=f"quick_sell_25_{crypto}"),
        InlineKeyboardButton("💰 Sell 50%", callback_data=f"quick_sell_50_{crypto}"),
        InlineKeyboardButton("💰 Sell 100%", callback_data=f"quick_sell_100_{crypto}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("⚙️ Manage SL/TP", callback_data=f"manage_sl_tp_{crypto}"),
        InlineKeyboardButton("🔙 Main Menu", callback_data="main")
    ])
    
    return InlineKeyboardMarkup(keyboard)


async def monitor_navigate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle navigation between trades"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    trades = trading_engine.get_active_trades(user_id)
    
    if not trades:
        await query.edit_message_text("No active trades.")
        return
    
    current_index = context.user_data.get('current_trade_index', 0)
    
    if query.data == "monitor_prev":
        current_index = max(0, current_index - 1)
    elif query.data == "monitor_next":
        current_index = min(len(trades) - 1, current_index + 1)
    elif query.data == "monitor_refresh":
        pass  # Just refresh current trade
    
    context.user_data['current_trade_index'] = current_index
    await show_trade_monitor(update, context, trades[current_index])


async def quick_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle quick sell buttons"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data_parts = query.data.split('_')
    percentage = int(data_parts[2])
    crypto = data_parts[3]
    
    trades = trading_engine.get_active_trades(user_id)
    current_index = context.user_data.get('current_trade_index', 0)
    
    if current_index >= len(trades):
        await query.edit_message_text("Trade not found.")
        return
    
    trade = trades[current_index]
    
    # Get user settings
    slippage = user_data[user_id]['wallets'][crypto]['SELL']['int']['SLIPPAGE']['value']
    gas_delta = user_data[user_id]['wallets'][crypto]['SELL']['int']['GAS_DELTA']['value']
    
    # Execute sell
    result = await trading_engine.sell_token(
        user_id, crypto, trade['token_address'], percentage, slippage, gas_delta
    )
    
    if result['success']:
        message = f"✅ Sell order placed!\n\n"
        message += f"Amount: {percentage}% of holdings\n"
        message += f"Tx: `{result['tx_hash']}`"
    else:
        message = f"❌ Sell failed: {result['error']}"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Monitor", callback_data="monitor_refresh")]]
    await query.edit_message_text(message, parse_mode="Markdown", 
                                  reply_markup=InlineKeyboardMarkup(keyboard))

#Maestro Sniper Bot
#
# -60%
#
# X Buy Dip
#
# V Auto-Sell
#
# Sell • GINNAN
#
# • Lo | Hi •
#
# 0.01 SOL -
#
# +1000%
#
# Threshold
#
# X Trailing
#
# PnL Card Buy
#
# Slippage: 30%
#
# Sell Initials
#
# 25% o Sell
#
# 50%
#
# Sell X SOL
#
# Reset Refresh • Gas Delta: 0.001 sol
#
# Sell X %
#
# 75% 100%
#
# Sell X Tokens
#
# Stop X Delete