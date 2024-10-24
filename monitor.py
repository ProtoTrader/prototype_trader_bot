from gc import callbacks

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
from user_data import user_data, init_user_data


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    print(user_data)
    if user_data == {} :
        firstname = update.effective_user.first_name
        init_user_data(user_id, firstname)
    #TODO : crypto devra etre la chain de la crypto qui serra afficher en premier dans le primary trade, donc sell qui c retrouver en premier dans le monitor
    crypto = 'SOL' # pour l'instant je met SOL pour tester
    await update.message.reply_text(monitor_menu_message(user_id), reply_markup=monitor_menu_keyboard(context, user_id, crypto))

async def monitor_original_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    crypto = "SOL" # pour l'instant je met SOL pour tester
    await query.answer()
    await query.edit_message_text(monitor_menu_message(user_id), reply_markup=monitor_menu_keyboard(context, user_id, crypto))

async def monitor_change_sell_low_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    crypto = "SOL" # pour l'instant je met SOL pour tester
    await query.answer()
    await query.edit_message_text(monitor_menu_message(user_id), reply_markup=monitor_menu_sell_low_symbol_keyboard(context, user_id, crypto))

async def monitor_change_sell_high_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    crypto = "SOL" # pour l'instant je met SOL pour tester
    await query.answer()
    await query.edit_message_text(monitor_menu_message(user_id), reply_markup=monitor_menu_sell_high_symbol_keyboard(context, user_id, crypto))

async def monitor_change_sell_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    crypto = "SOL" # pour l'instant je met SOL pour tester
    await query.answer()
    await query.edit_message_text(monitor_menu_message(user_id), reply_markup=monitor_menu_sell_amount_keyboard(context, user_id, crypto))

async def monitor_activate_auto_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    crypto = "SOL" # pour l'instant je met SOL pour tester
    await query.answer()
    user_data[user_id]['wallets'][crypto]['SELL']['bool']['AUTO_SELL']['value'] = not user_data[user_id]['wallets'][crypto]['SELL']['bool']['AUTO_SELL']['value']
    await query.edit_message_text(monitor_menu_message(user_id), reply_markup=monitor_menu_keyboard(context, user_id, crypto))

async def monitor_activate_trailing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    crypto = "SOL" # pour l'instant je met SOL pour tester
    await query.answer()
    user_data[user_id]['wallets'][crypto]['SELL']['bool']['TRAILING']['value'] = not user_data[user_id]['wallets'][crypto]['SELL']['bool']['TRAILING']['value']
    await query.edit_message_text(monitor_menu_message(user_id), reply_markup=monitor_menu_keyboard(context, user_id, crypto))

def monitor_menu_message(user_id) -> str:
    primary_text = primary_trade_text(user_id)
    other_text = other_trade_text(user_id)
    return primary_text + other_text


# 📌 Primary Trade
# 💳 Main
# 🪙 $VIORA (https://t.me/maestro?start=BhbfgSh5P742DE5eMx24iZXNZeD2vNRFBZe3EP9Mpump-cl_mentg) 🚀 +107.52% ⏱ 35:41
# Initial: 0.05 SOL
# Worth: 0.103 SOL
# Time elapsed: 17h 33m 35s
#
# 💵 Price: $0.0012 | MC: $1.2m
# 💸 Price impact: -0.03%
# 🤑 Expected payout: 0.1 SOL
#
# 🔧 DexT (https://www.dextools.io/app/solana/pair-explorer/GxUArM1uQg9ZEghuxn9Uc66h7Bv1J7vWkTUHr9jD8sHU) 📊 DexS (https://dexscreener.com/solana/GxUArM1uQg9ZEghuxn9Uc66h7Bv1J7vWkTUHr9jD8sHU) 📈 DexV (https://www.dexview.com/solana/BhbfgSh5P742DE5eMx24iZXNZeD2vNRFBZe3EP9Mpump) 👁 BirdEye (https://birdeye.so/token/BhbfgSh5P742DE5eMx24iZXNZeD2vNRFBZe3EP9Mpump?chain=solana)
#
# 🛍 Other Trades
# /1 🪙 automated 🚀 -97.70% ⏱ 18:27
#
# ℹ Sell-Lo/Hi compare against the coin's P/L, not its P/L w/tax
#
# 📢 Ad: Shill and get paid? No way. (https://x.com/MaestroBots/status/1844061260272250881)

def primary_trade_text(user_id) -> str:
    return """📌 Primary Trade
💳 Main
(ex)🪙 $VIORA 🚀 +123.03% ⏱ 35:51
Initial: 0.05 SOL
Worth: 0.111SOL
Time elapsed: 17h 23m 37s

💵 Price: $0.00128| MC: $1.29m
💸 Price impact: -0.03%
🤑 Expected payout: 0.11 SOL

🔧 DexT 📊 DexS 📈 DexV 👁 BirdEye"""

def other_trade_text(user_id) -> str:
    return """🛍 Other Trades
(ex)/1 🪙 automated 🚀 -97.70% ⏱ 18:35

ℹ Use ⬅ | ➡ to switch between multiple trades

 📢 Ad: Shill and get paid? No way."""

def monitor_menu_keyboard(context: ContextTypes.DEFAULT_TYPE, user_id, crypto) -> InlineKeyboardMarkup:
    # TODO: for each conv, change the value only for the crypto currently displayed in the primary trade of the monitor
    keyboard = [
        button_bot_name(),
        [InlineKeyboardButton("←", callback_data="previous_coin_" + crypto),
         InlineKeyboardButton("🔃 Viora", callback_data="refresh_actual_coin_" + crypto),
         InlineKeyboardButton("→", callback_data="next_coin_" + crypto)],
        [InlineKeyboardButton(get_sell_low_text(user_id, crypto), callback_data="monitor_change_sell_low_value_" + crypto),
         InlineKeyboardButton("Lo | Hi", callback_data="change_menu_sell_to_amount_" + crypto),
         InlineKeyboardButton(get_sell_high_text(user_id, crypto), callback_data="monitor_change_sell_high_value_" + crypto)],
        [InlineKeyboardButton("X Buy Dip", callback_data="activate_buy_dip_monitor_" + crypto),
         InlineKeyboardButton("0.01 SOL", callback_data="cv_change_value_buy_dip_" + crypto),
         InlineKeyboardButton("Threshold", callback_data="menu_threshold_monitor_" + crypto)],
        [InlineKeyboardButton(get_booloean_button_text(user_id,crypto,"AUTO_SELL"), callback_data="activate_auto_sell_monitor_" + crypto),
         InlineKeyboardButton(get_booloean_button_text(user_id,crypto,"TRAILING"), callback_data="activate_trailing_monitor_" + crypto)],
        [InlineKeyboardButton("Sell <=> BUY", callback_data="menu_change_sell_buy_" + crypto),
         InlineKeyboardButton("PnL Card Buy", callback_data="create_pnl_card_buy_" + crypto)],
        [InlineKeyboardButton(get_slippage_text(user_id, crypto), callback_data="cv_change_slippage_" + crypto),
         InlineKeyboardButton(get_gas_delta_text(user_id, crypto), callback_data="cv_change_gas_delta_" + crypto)],
        [InlineKeyboardButton("Sell Initials", callback_data="sell_initials_amount_" + crypto),
         InlineKeyboardButton("Nuke Sell", callback_data="nuke_sell_" + crypto),
         InlineKeyboardButton("Sell X %", callback_data="cv_sell_x_pourcentage_" + crypto)],
        [InlineKeyboardButton("25% o Sell", callback_data="sell_x_pourcentage_first_button_" + crypto),
         InlineKeyboardButton("50%", callback_data="sell_x_pourcentage_second_button_" + crypto),
         InlineKeyboardButton("75%", callback_data="sell_x_pourcentage_third_button_" + crypto),
         InlineKeyboardButton("100%", callback_data="sell_x_pourcentage_fourth_button_" + crypto)],
        [InlineKeyboardButton("Sell X SOL", callback_data="cv_sell_x_sol_" + crypto),
         InlineKeyboardButton("Sell X Tokens", callback_data="cv_sell_x_tokens_" + crypto)],
        [InlineKeyboardButton("Reset", callback_data="reset_monitor_" + crypto),
         InlineKeyboardButton("Refresh", callback_data="refresh_monitor_" + crypto),
         InlineKeyboardButton("Stop", callback_data="stop_monitor_" + crypto),
         InlineKeyboardButton("Delete", callback_data="delete_monitor_" + crypto)]
    ]
    return InlineKeyboardMarkup(keyboard)

def monitor_menu_sell_low_symbol_keyboard(context: ContextTypes.DEFAULT_TYPE, user_id, crypto) -> InlineKeyboardMarkup:
    keyboard = [
        button_bot_name(),
        [InlineKeyboardButton("←", callback_data="previous_coin_" + crypto),
         InlineKeyboardButton("🔃 Viora", callback_data="refresh_actual_coin_" + crypto),
         InlineKeyboardButton("→", callback_data="next_coin_" + crypto)],
        [InlineKeyboardButton("%", callback_data="cv_change_sell_low_value_by_pourcentage_" + crypto),
         InlineKeyboardButton("Price", callback_data="cv_change_sell_low_value_by_price_" + crypto),
         InlineKeyboardButton("MC", callback_data="cv_change_sell_low_value_by_mc_" + crypto),
         InlineKeyboardButton("X", callback_data="monitor_original_menu")],
        [InlineKeyboardButton("X Buy Dip", callback_data="activate_buy_dip_monitor_" + crypto),
         InlineKeyboardButton("0.01 SOL", callback_data="cv_change_value_buy_dip_" + crypto),
         InlineKeyboardButton("Threshold", callback_data="menu_threshold_monitor_" + crypto)],
        [InlineKeyboardButton(get_booloean_button_text(user_id,crypto,"AUTO_SELL"), callback_data="activate_auto_sell_monitor_" + crypto),
         InlineKeyboardButton(get_booloean_button_text(user_id,crypto,"TRAILING"), callback_data="activate_trailing_monitor_" + crypto)],
        [InlineKeyboardButton("Sell <=> BUY", callback_data="menu_change_sell_buy_" + crypto),
         InlineKeyboardButton("PnL Card Buy", callback_data="create_pnl_card_buy_" + crypto)],
        [InlineKeyboardButton(get_slippage_text(user_id, crypto), callback_data="cv_change_slippage_" + crypto),
         InlineKeyboardButton(get_gas_delta_text(user_id, crypto), callback_data="cv_change_gas_delta_" + crypto)],
        [InlineKeyboardButton("Sell Initials", callback_data="sell_initials_amount_" + crypto),
         InlineKeyboardButton("Nuke Sell", callback_data="nuke_sell_" + crypto),
         InlineKeyboardButton("Sell X %", callback_data="cv_sell_x_pourcentage_" + crypto)],
        [InlineKeyboardButton("25% o Sell", callback_data="sell_x_pourcentage_first_button_" + crypto),
         InlineKeyboardButton("50%", callback_data="sell_x_pourcentage_second_button_" + crypto),
         InlineKeyboardButton("75%", callback_data="sell_x_pourcentage_third_button_" + crypto),
         InlineKeyboardButton("100%", callback_data="sell_x_pourcentage_fourth_button_" + crypto)],
        [InlineKeyboardButton("Sell X SOL", callback_data="cv_sell_x_sol_" + crypto),
         InlineKeyboardButton("Sell X Tokens", callback_data="cv_sell_x_tokens_" + crypto)],
        [InlineKeyboardButton("Reset", callback_data="reset_monitor_" + crypto),
         InlineKeyboardButton("Refresh", callback_data="refresh_monitor_" + crypto),
         InlineKeyboardButton("Stop", callback_data="stop_monitor_" + crypto),
         InlineKeyboardButton("Delete", callback_data="delete_monitor_" + crypto)]
    ]
    return InlineKeyboardMarkup(keyboard)

def monitor_menu_sell_high_symbol_keyboard(context: ContextTypes.DEFAULT_TYPE, user_id, crypto) -> InlineKeyboardMarkup:
    keyboard = [
        button_bot_name(),
        [InlineKeyboardButton("←", callback_data="previous_coin_" + crypto),
         InlineKeyboardButton("🔃 Viora", callback_data="refresh_actual_coin_" + crypto),
         InlineKeyboardButton("→", callback_data="next_coin_" + crypto)],
        [InlineKeyboardButton("%", callback_data="cv_change_sell_high_value_by_pourcentage_" + crypto),
         InlineKeyboardButton("Price", callback_data="cv_change_sell_high_value_by_price_" + crypto),
         InlineKeyboardButton("MC", callback_data="cv_change_sell_high_value_by_mc_" + crypto),
         InlineKeyboardButton("X", callback_data="monitor_original_menu")],
        [InlineKeyboardButton("X Buy Dip", callback_data="activate_buy_dip_monitor_" + crypto),
         InlineKeyboardButton("0.01 SOL", callback_data="cv_change_value_buy_dip_" + crypto),
         InlineKeyboardButton("Threshold", callback_data="menu_threshold_monitor_" + crypto)],
        [InlineKeyboardButton(get_booloean_button_text(user_id,crypto,"AUTO_SELL"), callback_data="activate_auto_sell_monitor_" + crypto),
         InlineKeyboardButton(get_booloean_button_text(user_id,crypto,"TRAILING"), callback_data="activate_trailing_monitor_" + crypto)],
        [InlineKeyboardButton("Sell <=> BUY", callback_data="menu_change_sell_buy_" + crypto),
         InlineKeyboardButton("PnL Card Buy", callback_data="create_pnl_card_buy_" + crypto)],
        [InlineKeyboardButton(get_slippage_text(user_id, crypto), callback_data="cv_change_slippage_" + crypto),
         InlineKeyboardButton(get_gas_delta_text(user_id, crypto), callback_data="cv_change_gas_delta_" + crypto)],
        [InlineKeyboardButton("Sell Initials", callback_data="sell_initials_amount_" + crypto),
         InlineKeyboardButton("Nuke Sell", callback_data="nuke_sell_" + crypto),
         InlineKeyboardButton("Sell X %", callback_data="cv_sell_x_pourcentage_" + crypto)],
        [InlineKeyboardButton("25% o Sell", callback_data="sell_x_pourcentage_first_button_" + crypto),
         InlineKeyboardButton("50%", callback_data="sell_x_pourcentage_second_button_" + crypto),
         InlineKeyboardButton("75%", callback_data="sell_x_pourcentage_third_button_" + crypto),
         InlineKeyboardButton("100%", callback_data="sell_x_pourcentage_fourth_button_" + crypto)],
        [InlineKeyboardButton("Sell X SOL", callback_data="cv_sell_x_sol_" + crypto),
         InlineKeyboardButton("Sell X Tokens", callback_data="cv_sell_x_tokens_" + crypto)],
        [InlineKeyboardButton("Reset", callback_data="reset_monitor_" + crypto),
         InlineKeyboardButton("Refresh", callback_data="refresh_monitor_" + crypto),
         InlineKeyboardButton("Stop", callback_data="stop_monitor_" + crypto),
         InlineKeyboardButton("Delete", callback_data="delete_monitor_" + crypto)]
    ]
    return InlineKeyboardMarkup(keyboard)

def monitor_menu_sell_amount_keyboard(context: ContextTypes.DEFAULT_TYPE, user_id, crypto) -> InlineKeyboardMarkup:
    keyboard = [
        button_bot_name(),
        [InlineKeyboardButton("←", callback_data="previous_coin_" + crypto),
         InlineKeyboardButton("🔃 Viora", callback_data="refresh_actual_coin_" + crypto),
         InlineKeyboardButton("→", callback_data="next_coin_" + crypto)],
        [InlineKeyboardButton(get_sell_low_amount_text(user_id,crypto), callback_data="cv_monitor_change_sell_low_amount_" + crypto),
         InlineKeyboardButton("< Amount >", callback_data="monitor_original_menu"),
         InlineKeyboardButton(get_sell_high_amount_text(user_id,crypto), callback_data="cv_monitor_change_sell_high_amount_" + crypto)],
        [InlineKeyboardButton("X Buy Dip", callback_data="activate_buy_dip_monitor_" + crypto),
         InlineKeyboardButton("0.01 SOL", callback_data="cv_change_value_buy_dip_" + crypto),
         InlineKeyboardButton("Threshold", callback_data="menu_threshold_monitor_" + crypto)],
        [InlineKeyboardButton(get_booloean_button_text(user_id,crypto,"AUTO_SELL"), callback_data="activate_auto_sell_monitor_" + crypto),
         InlineKeyboardButton(get_booloean_button_text(user_id,crypto,"TRAILING"), callback_data="activate_trailing_monitor_" + crypto)],
        [InlineKeyboardButton("Sell <=> BUY", callback_data="menu_change_sell_buy_" + crypto),
         InlineKeyboardButton("PnL Card Buy", callback_data="create_pnl_card_buy_" + crypto)],
        [InlineKeyboardButton(get_slippage_text(user_id, crypto), callback_data="cv_change_slippage_" + crypto),
         InlineKeyboardButton(get_gas_delta_text(user_id, crypto), callback_data="cv_change_gas_delta_" + crypto)],
        [InlineKeyboardButton("Sell Initials", callback_data="sell_initials_amount_" + crypto),
         InlineKeyboardButton("Nuke Sell", callback_data="nuke_sell_" + crypto),
         InlineKeyboardButton("Sell X %", callback_data="cv_sell_x_pourcentage_" + crypto)],
        [InlineKeyboardButton("25% o Sell", callback_data="sell_x_pourcentage_first_button_" + crypto),
         InlineKeyboardButton("50%", callback_data="sell_x_pourcentage_second_button_" + crypto),
         InlineKeyboardButton("75%", callback_data="sell_x_pourcentage_third_button_" + crypto),
         InlineKeyboardButton("100%", callback_data="sell_x_pourcentage_fourth_button_" + crypto)],
        [InlineKeyboardButton("Sell X SOL", callback_data="cv_sell_x_sol_" + crypto),
         InlineKeyboardButton("Sell X Tokens", callback_data="cv_sell_x_tokens_" + crypto)],
        [InlineKeyboardButton("Reset", callback_data="reset_monitor_" + crypto),
         InlineKeyboardButton("Refresh", callback_data="refresh_monitor_" + crypto),
         InlineKeyboardButton("Stop", callback_data="stop_monitor_" + crypto),
         InlineKeyboardButton("X Delete", callback_data="delete_monitor_" + crypto)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_booloean_button_text(user_id, crypto, bool_name) -> str :
    #TODO : pas pour buy dip car specifique a chaque token, pareil pour delete
    value = user_data[user_id]['wallets'][crypto]['SELL']['bool'][bool_name]['value']
    text = "V " + bool_name if value else "X " + bool_name
    return text

def get_sell_low_text(user_id, crypto) -> str :
    #TODO : si cela vien d'un copy trade mettre les valeur a celle parametrer dans les parametres du trader copier
    data = user_data[user_id]['wallets'][crypto]['SELL']['int']['SELL_LOW']
    text = str(data['value']) + data['symbol']
    return text

def get_sell_high_text(user_id, crypto) -> str :
    # TODO : si cela vien d'un copy trade mettre les valeur a celle parametrer dans les parametres du trader copier
    data = user_data[user_id]['wallets'][crypto]['SELL']['int']['SELL_HIGH']
    text = str(data['value']) + data['symbol']
    return text

def get_slippage_text(user_id, crypto) -> str :
    # TODO : si cela vien d'un copy trade mettre les valeur a celle parametrer dans les parametres du trader copier
    data = user_data[user_id]['wallets'][crypto]['SELL']['int']['SLIPPAGE']
    text = "Slippage : " + str(data['value'])  + data['symbol']
    return text

def get_gas_delta_text(user_id, crypto) -> str :
    # TODO : si cela vien d'un copy trade mettre les valeur a celle parametrer dans les parametres du trader copier
    data = user_data[user_id]['wallets'][crypto]['SELL']['int']['GAS_DELTA']
    text = "$Gas Delta " + str(data['value']) + " " + crypto
    return text

def get_sell_low_amount_text(user_id, crypto) -> str :
    #TODO : function that return the value of the sell low amount
    data = user_data[user_id]['wallets'][crypto]['SELL']['int']['SELL_LOW_AMOUNT']
    text = str(data['value']) + data['symbol']
    return text

def get_sell_high_amount_text(user_id, crypto) -> str :
    #TODO : function that return the value of the sell high amount
    data = user_data[user_id]['wallets'][crypto]['SELL']['int']['SELL_HIGH_AMOUNT']
    text = str(data['value']) + data['symbol']
    return text

#TODO : function that return the text for the four button of the sell x pourcentage because they can be edited to change the value of the sell x pourcentage