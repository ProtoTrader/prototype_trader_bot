from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application,
                          CommandHandler,
                          CallbackQueryHandler,
                          ConversationHandler,
                          MessageHandler,
                          ContextTypes,
                          filters
                          )
from button import *
from user_data import user_data, message_ids, reply_message_conv, delete_conv
from copy_trading_engine import copy_trading_engine
import re
import json

copytrade_message_id = None
copytrade_context = None
copytrade_update = None

# Wallet regex patterns for different types
wallet_regex = {
    'SOL': r'[1-9A-HJ-NP-Za-km-z]{32,44}',  # Solana
    'ETH': r'^0x[a-fA-F0-9]{40}$',  # Ethereum
    'TRX': r'^T[a-zA-Z0-9]{33}$'  # TRX
}

MAX_WALLETS_FREE = 3
AWAITING_WALLET, AWAITING_NAME = range(2)

async def ct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    print("Open copy trade menu for " + query.data.split('_')[-1] + "...")
    print(query.data)
    await query.edit_message_text("Copy Trade Menu", reply_markup=copytrade_menu_keyboard(context, user_id))

def copytrade_menu_keyboard(context: ContextTypes.DEFAULT_TYPE, user_id) -> InlineKeyboardMarkup:
    keyboard = [
        button_bot_name(),
        [InlineKeyboardButton("🔙 Return", callback_data='main')],  # Return to main menu
    ]
    for chain in user_data[user_id]['chain_states']:
        print(chain)
        if user_data[user_id]['chain_states'][chain]:
            keyboard.append(
                [InlineKeyboardButton(get_button_chain_name(chain), callback_data='show_copytrade_' + chain)])
    return InlineKeyboardMarkup(keyboard)

async def show_copytrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global copytrade_message_id
    global copytrade_context
    global copytrade_update
    query = update.callback_query
    user_id = query.from_user.id
    crypto = query.data.split('_')[-1]
    await query.answer()
    print("Showing copy trade for " + query.data.split('_')[-1] + "...")
    print(query.data)
    message = await query.edit_message_text("Copy Trade Menu",
                                            reply_markup=copytrade_crypto_keyboard(context, user_id, crypto))
    copytrade_context = context
    copytrade_update = update
    copytrade_message_id = message.message_id

def copytrade_crypto_keyboard(context: ContextTypes.DEFAULT_TYPE, user_id, crypto) -> InlineKeyboardMarkup:
    keyboard = [
        button_bot_name(),
        [InlineKeyboardButton(get_button_text_ct(crypto, user_id), callback_data='set_copy_trade_' + crypto),
         InlineKeyboardButton("🔙 Return", callback_data='ct')],
        [InlineKeyboardButton("Add Wallet or Contract", callback_data='add_ct_wallet_' + crypto)],
    ]

    if user_data[user_id]['wallets'][crypto]['GENERAL']['WALLETS_CT']['value']:
        for i in user_data[user_id]['wallets'][crypto]['GENERAL']['WALLETS_CT']['value']:
            for wallet in i:
                print(i)
                print(wallet)
                keyboard.append(
                    [InlineKeyboardButton(i[wallet]['name'], callback_data='param_ct_wallet_' + crypto + '_' + wallet),
                     InlineKeyboardButton("Rename", callback_data='rename_ct_wallet_' + crypto + '_' + wallet),
                     InlineKeyboardButton("❌", callback_data='remove_ct_wallet_' + crypto + '_' + wallet)])
    return InlineKeyboardMarkup(keyboard)

def get_button_text_ct(chain_name: str, user_id) -> str:
    if chain_name in user_data[user_id]['wallets']:
        return "🟢 ON" if user_data[user_id]['wallets'][chain_name]['BUY']['bool']['COPY_TRADE']['value'] else "🔴 OFF"


async def set_copytrade_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    crypto = query.data.split('_')[-1]
    await query.answer()
    if crypto in user_data[user_id]['wallets']:
        user_data[user_id]['wallets'][crypto]['BUY']['bool']['COPY_TRADE']['value'] = not \
            user_data[user_id]['wallets'][crypto]['BUY']['bool']['COPY_TRADE']['value']
    print("Copy Trade for " + crypto + "...")
    print(query.data)
    await query.edit_message_text("Copy Trade Menu", reply_markup=copytrade_crypto_keyboard(context, user_id, crypto))


async def add_wallet_ct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # User clicked a button for adding a specific wallet type
    print("add_wallet_ct")
    query = update.callback_query
    context.user_data['wallet_type'] = query.data.split('_')[-1]
    crypto = context.user_data['wallet_type']
    await query.answer()
    # Ask for wallet address in a new message
    message = await query.message.reply_text("Please provide the wallet address:")

    # Store the message ID to delete later
    user_id = update.effective_user.id
    if user_id not in message_ids:
        message_ids[user_id] = {'bot': [], 'user': []}
    message_ids[user_id]['bot'].append(message.message_id)

    return AWAITING_WALLET


async def receive_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Get the selected wallet type
    wallet_type = context.user_data.get('wallet_type')
    wallet_address = update.message.text
    user_id = update.effective_user.id

    # Validate the wallet address using the regex for the selected wallet type
    if re.match(wallet_regex[wallet_type], wallet_address):
        # Save the wallet address in the user data
        context.user_data['wallet_address'] = wallet_address
        message = await update.message.reply_text("Wallet address is valid! Please provide a name for this wallet:")

        # Store the message ID to delete later
        if user_id not in message_ids:
            message_ids[user_id] = {'bot': [], 'user': []}
        message_ids[user_id]['user'].append(update.message.message_id)
        message_ids[user_id]['bot'].append(message.message_id)

        return AWAITING_NAME
    else:
        message = await update.message.reply_text("Invalid wallet address. Please provide a correct wallet address:")

        # Store the message ID to delete later
        if user_id not in message_ids:
            message_ids[user_id] = {'bot': [], 'user': []}
        message_ids[user_id]['user'].append(update.message.message_id)
        message_ids[user_id]['bot'].append(message.message_id)

        return AWAITING_WALLET


async def receive_wallet_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Receive the wallet name
    wallet_name = update.message.text
    wallet_address = context.user_data.get('wallet_address')
    wallet_type = context.user_data.get('wallet_type')
    user_id = update.effective_user.id

    wallets_ct = user_data[user_id]['wallets'][wallet_type]['GENERAL']['WALLETS_CT']['value']

    # Check if wallet address already exists
    if wallet_address in wallets_ct:
        message = await update.message.reply_text("This wallet address already exists.")

        # Store the message ID to delete later
        if user_id not in message_ids:
            message_ids[user_id] = {'bot': [], 'user': []}
        message_ids[user_id]['user'].append(update.message.message_id)
        message_ids[user_id]['bot'].append(message.message_id)
    else:
        # Check if the user is subscribed and limit the number of wallets
        is_subscribed = user_data[user_id]['subscribed']
        if not is_subscribed and len(wallets_ct) >= MAX_WALLETS_FREE:
            message = await update.message.reply_text(
                f"You cannot add more than {MAX_WALLETS_FREE} wallets in the free version.")

            # Store the message ID to delete later
            if user_id not in message_ids:
                message_ids[user_id] = {'bot': [], 'user': []}
            message_ids[user_id]['user'].append(update.message.message_id)
            message_ids[user_id]['bot'].append(message.message_id)
        else:
            # Add wallet to the list
            # generate a i value for wallet
            i = len(user_data[user_id]['wallets'][wallet_type]['GENERAL']['WALLETS_CT']['value'])
            to_input = {
                f'{i}': {
                    'address': wallet_address,
                    'name': wallet_name
                }
            }
            wallets_ct.append(to_input)
            user_data[user_id]['wallets'][wallet_type]['GENERAL']['WALLETS_CT']['value'] = wallets_ct
            
            # Add wallet to copy trading engine monitoring
            copy_trading_engine.add_wallet_to_monitor(wallet_type, wallet_address, user_id)
            
            text = f"Wallet '{wallet_name}' with address '{wallet_address}' added successfully to Copy Trade!"
            await reply_message_conv(update, user_id, text)

    await delete_conv(update, user_id)

    user_data_json = json.dumps(user_data, indent=4, ensure_ascii=False)
    print(user_data_json)

    return ConversationHandler.END





async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Cancel the current conversation
    await update.message.reply_text("Operation cancelled.")

    return ConversationHandler.END
