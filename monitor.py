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
from chain_menu import chain_menu
from user_data import user_data


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    crypto = update.callback_query.data.split('_')[-1]
    await update.message.reply_text(monitor_menu_message(user_id), reply_markup=monitor_menu_keyboard(context, user_id, crypto))

def monitor_menu_message(user_id) -> str:
    primary_text = primary_trade_text(user_id)
    other_text = other_trade_text(user_id)
    return primary_text + other_text

def primary_trade_text(user_id) -> str:
    return """📌 Primary Trade
💳 Main
(ex)🪙 $GINNAN 🚀 -0.87% ⏱ 33:51
Initial: 0.05 SOL
Worth: 0.0495 SOL
Time elapsed: 2h 8m 49s

💵 Price: $0.00000218 | MC: $15.05m
💸 Price impact: -0.00%
🤑 Expected payout: 0.049 SOL

🔧 DexT 📊 DexS 📈 DexV 👁 BirdEye"""

def other_trade_text(user_id) -> str:
    return """🛍 Other Trades
(ex)/1 🪙 NIGGA 🚀 -3.64% ⏱ 21:08

ℹ Use ⬅ | ➡ to switch between multiple trades

 📢 Ad: Shill and get paid? No way."""

def monitor_menu_keyboard(context: ContextTypes.DEFAULT_TYPE, user_id, crypto) -> InlineKeyboardMarkup:
    keyboard = [
        button_bot_name(),
        [InlineKeyboardButton("←", "previous_coin_" + crypto), InlineKeyboardButton("🔃 Ginnan", "refresh_actual_coin_" + crypto),InlineKeyboardButton("→", "next_coin_" + crypto)],
        [InlineKeyboardButton("←", "previous_coin_" + crypto),InlineKeyboardButton("←", "previous_coin_" + crypto),InlineKeyboardButton("←", "previous_coin_" + crypto)]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_low_sl_text(context: ContextTypes.DEFAULT_TYPE, user_id, crypto) -> str :
    #TODO : si cela vien d'un copy trade mettre les valeur a celle parametrer dans les parametres du trader copier
    data = user_data[user_id][crypto]['SELL']['SELL_LOW']
    text = data['value'] + data['symbol']
    return text

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