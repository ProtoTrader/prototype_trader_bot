"""
Trading Commands - Telegram bot handlers for trading operations
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from user_data import user_data, reply_message_conv
from trading_engine import trading_engine
import re

# Conversation states
AWAITING_TOKEN_ADDRESS, AWAITING_AMOUNT, AWAITING_CONFIRMATION = range(3)


async def start_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start buy process"""
    query = update.callback_query
    await query.answer()
    
    crypto = query.data.split('_')[-1]
    user_id = query.from_user.id
    
    # Check if wallet is connected
    has_wallet = False
    if 'connected_wallets' in user_data[user_id] and crypto in user_data[user_id]['connected_wallets']:
        has_wallet = True
    elif 'generated_wallets' in user_data[user_id] and crypto in user_data[user_id]['generated_wallets']:
        has_wallet = True
    
    if not has_wallet:
        await query.edit_message_text(
            f"❌ No wallet connected for {crypto}!\n"
            "Please generate or connect a wallet first.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data=f"show_wallet_{crypto}")
            ]])
        )
        return ConversationHandler.END
    
    context.user_data['trading_chain'] = crypto
    context.user_data['trading_type'] = 'buy'
    
    message = f"🛒 Buy Token on {crypto}\n\n"
    message += "Please send the token contract address:\n"
    message += "Type /cancel to cancel."
    
    await query.edit_message_text(message)
    return AWAITING_TOKEN_ADDRESS


async def start_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start sell process"""
    query = update.callback_query
    await query.answer()
    
    crypto = query.data.split('_')[-1]
    user_id = query.from_user.id
    
    # Check if wallet is connected
    has_wallet = False
    if 'connected_wallets' in user_data[user_id] and crypto in user_data[user_id]['connected_wallets']:
        has_wallet = True
    elif 'generated_wallets' in user_data[user_id] and crypto in user_data[user_id]['generated_wallets']:
        has_wallet = True
    
    if not has_wallet:
        await query.edit_message_text(
            f"❌ No wallet connected for {crypto}!\n"
            "Please generate or connect a wallet first.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data=f"show_wallet_{crypto}")
            ]])
        )
        return ConversationHandler.END
    
    context.user_data['trading_chain'] = crypto
    context.user_data['trading_type'] = 'sell'
    
    message = f"💰 Sell Token on {crypto}\n\n"
    message += "Please send the token contract address:\n"
    message += "Type /cancel to cancel."
    
    await query.edit_message_text(message)
    return AWAITING_TOKEN_ADDRESS


async def receive_token_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and validate token address"""
    user_id = update.effective_user.id
    token_address = update.message.text.strip()
    crypto = context.user_data.get('trading_chain')
    
    # Basic validation
    if crypto == 'ETH' and not re.match(r'^0x[a-fA-F0-9]{40}$', token_address):
        await reply_message_conv(update, user_id, "❌ Invalid Ethereum token address. Please try again.")
        return AWAITING_TOKEN_ADDRESS
    elif crypto == 'SOL' and len(token_address) < 32:
        await reply_message_conv(update, user_id, "❌ Invalid Solana token address. Please try again.")
        return AWAITING_TOKEN_ADDRESS
    elif crypto == 'TRX' and not token_address.startswith('T'):
        await reply_message_conv(update, user_id, "❌ Invalid Tron token address. Please try again.")
        return AWAITING_TOKEN_ADDRESS
    
    context.user_data['token_address'] = token_address
    
    trade_type = context.user_data.get('trading_type')
    message = f"Token: `{token_address}`\n\n"
    
    if trade_type == 'buy':
        message += f"How much {crypto} do you want to spend?\n"
        message += "Example: 0.1"
    else:
        message += "What percentage of your tokens do you want to sell?\n"
        message += "Example: 50 (for 50%)"
    
    await update.message.reply_text(message, parse_mode="Markdown")
    return AWAITING_AMOUNT


async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive trade amount"""
    user_id = update.effective_user.id
    
    try:
        amount = float(update.message.text.strip())
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        context.user_data['amount'] = amount
        
        # Get user settings
        crypto = context.user_data.get('trading_chain')
        trade_type = context.user_data.get('trading_type')
        token_address = context.user_data.get('token_address')
        
        # Get trading parameters
        if trade_type == 'buy':
            slippage = user_data[user_id]['wallets'][crypto]['BUY']['int']['SLIPPAGE']['value']
            gas_delta = user_data[user_id]['wallets'][crypto]['BUY']['int']['GAS_DELTA']['value']
            pia = user_data[user_id]['wallets'][crypto]['BUY']['int']['PIA']['value']
        else:
            slippage = user_data[user_id]['wallets'][crypto]['SELL']['int']['SLIPPAGE']['value']
            gas_delta = user_data[user_id]['wallets'][crypto]['SELL']['int']['GAS_DELTA']['value']
            pia = user_data[user_id]['wallets'][crypto]['SELL']['int']['PIA']['value']
        
        # Build confirmation message
        message = f"📋 **Trade Confirmation**\n\n"
        message += f"Type: **{trade_type.upper()}**\n"
        message += f"Chain: **{crypto}**\n"
        message += f"Token: `{token_address}`\n"
        
        if trade_type == 'buy':
            message += f"Amount: **{amount} {crypto}**\n"
        else:
            message += f"Amount: **{amount}%** of holdings\n"
        
        message += f"\n⚙️ **Settings:**\n"
        message += f"Slippage: {slippage}%\n"
        message += f"Gas Delta: {gas_delta}\n"
        message += f"Price Impact Alert: {pia}%\n"
        
        message += "\n⚠️ **Warning:** This will execute a real transaction!\n"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="confirm_trade"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_trade")
            ]
        ]
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return AWAITING_CONFIRMATION
        
    except ValueError:
        await reply_message_conv(update, user_id, "❌ Invalid amount. Please enter a valid number.")
        return AWAITING_AMOUNT


async def confirm_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Execute the trade after confirmation"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "cancel_trade":
        await query.edit_message_text("❌ Trade cancelled.")
        return ConversationHandler.END
    
    # Get trade details
    crypto = context.user_data.get('trading_chain')
    trade_type = context.user_data.get('trading_type')
    token_address = context.user_data.get('token_address')
    amount = context.user_data.get('amount')
    
    # Get trading parameters
    if trade_type == 'buy':
        slippage = user_data[user_id]['wallets'][crypto]['BUY']['int']['SLIPPAGE']['value']
        gas_delta = user_data[user_id]['wallets'][crypto]['BUY']['int']['GAS_DELTA']['value']
    else:
        slippage = user_data[user_id]['wallets'][crypto]['SELL']['int']['SLIPPAGE']['value']
        gas_delta = user_data[user_id]['wallets'][crypto]['SELL']['int']['GAS_DELTA']['value']
    
    # Update message
    await query.edit_message_text("🔄 Executing trade...")
    
    # Execute trade
    if trade_type == 'buy':
        result = await trading_engine.buy_token(
            user_id, crypto, token_address, amount, slippage, gas_delta
        )
    else:
        result = await trading_engine.sell_token(
            user_id, crypto, token_address, amount, slippage, gas_delta
        )
    
    # Show result
    if result['success']:
        message = f"✅ **Trade Successful!**\n\n"
        message += f"Trade ID: `{result['trade_id']}`\n"
        message += f"Transaction: `{result['tx_hash']}`\n\n"
        
        # Check if auto sell or stop loss is enabled
        if trade_type == 'buy':
            auto_sell = user_data[user_id]['wallets'][crypto]['SELL']['bool']['AUTO_SELL']['value']
            if auto_sell:
                sell_high = user_data[user_id]['wallets'][crypto]['SELL']['int']['SELL_HIGH']['value']
                sell_low = user_data[user_id]['wallets'][crypto]['SELL']['int']['SELL_LOW']['value']
                
                # Set stop loss and take profit
                await trading_engine.set_stop_loss(result['trade_id'], abs(sell_low))
                await trading_engine.set_take_profit(result['trade_id'], sell_high)
                
                message += f"📊 Auto-sell enabled:\n"
                message += f"Take Profit: +{sell_high}%\n"
                message += f"Stop Loss: {sell_low}%"
    else:
        message = f"❌ **Trade Failed**\n\n"
        message += f"Error: {result['error']}"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Wallet", callback_data=f"show_wallet_{crypto}")]]
    
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END


async def cancel_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel ongoing trade"""
    await update.message.reply_text("❌ Trade cancelled.")
    return ConversationHandler.END


def get_trading_keyboard(crypto: str) -> InlineKeyboardMarkup:
    """Get trading action keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🛒 Buy", callback_data=f"start_buy_{crypto}"),
            InlineKeyboardButton("💰 Sell", callback_data=f"start_sell_{crypto}")
        ],
        [
            InlineKeyboardButton("📊 Active Trades", callback_data=f"show_trades_{crypto}"),
            InlineKeyboardButton("🔙 Back", callback_data=f"show_wallet_{crypto}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)