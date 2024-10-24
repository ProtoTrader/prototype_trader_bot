import os

from dotenv import load_dotenv

from chain_menu import *
from copy_trade import *
from faq_menu import *
from main_menu import *
from wallets import *
from monitor import *

load_dotenv()

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in user_data:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        user_data[user_id] = {
            'first_name': first_name,
            'id': user_id,
            'subscribed': False,
        }
        print(user_data)
        user_data[user_id]['chain_states'] = {
            'SOL': True,
            'ETH': False,
            'TRX': False,
        }
        user_data[user_id]['wallets'] = {
            'SOL': {
                'GENERAL': {
                    'WALLETS_CT': {
                        'value': [],
                        'text': "Wallets CT",
                        'name': "Wallets d'adresse du  Copy Trade : "
                    },
                },
                'BUY': {
                    'bool': {
                        'COPY_TRADE': {
                            'value': False,
                            'text': "Off",
                            'name': "Copy Trade Buy : "
                        },
                        'CONFIRM_TRADE': {
                            'value': False,
                            'text': "Confirm Trade",
                            'name': "Confirm Trade Buy : "
                        },
                        'DUPE_BUY': {
                            'value': False,
                            'text': "Dupe Buy",
                            'name': "Duplicate Buy : "
                        },
                        'AUTO_BUY': {
                            'value': False,
                            'text': "Auto Buy",
                            'name': "Auto Buy : "
                        },
                    },
                    'int': {
                        'MIN_MC': {
                            'value': 0,
                            'text': "Min Mc",
                            'name': "Min MCap : "
                        },
                        'MAX_MC': {
                            'value': 0,
                            'text': "Max Mc",
                            'name': "Max MCap : "
                        },
                        'MIN_LIQ': {
                            'value': 0,
                            'text': "Min Liquidity",
                            'name': "Min Liquidity : "
                        },
                        'MAX_LIQ': {
                            'value': 0,
                            'text': "Max Liquidity",
                            'name': "Max Liquidity : "
                        },
                        'MIN_MC_LIQ': {
                            'value': 0,
                            'text': "Min Mc/Liq",
                            'name': "Min MCap/Liq : "
                        },
                        'GAS_DELTA': {
                            'value': 0.001,
                            'text': "Gas Delta",
                            'name': "Buy Gas Delta : "
                        },
                        'PIA': {
                            'value': 25,
                            'text': "Price Impact Alert",
                            'name': "Price impact alert : "
                        },
                        'SLIPPAGE': {
                            'value': 10,
                            'text': "Slippage",
                            'name': "Slippage : "
                        },
                    },
                },
                'SELL': {
                    'bool': {
                        'CONFIRM_TRADE': {
                            'value': False,
                            'text': "Confirm Trade",
                            'name': "Confirm Trade Sell : "
                        },
                        'AUTO_SELL': {
                            'value': False,
                            'text': "Auto Sell",
                            'name': "Auto Sell : "
                        },
                        'TRAILING_SELL': {
                            'value': False,
                            'text': "Trailing Sell",
                            'name': "Trailing Sell : "
                        },
                        'AUTO_SELL_RETRY': {
                            'value': False,
                            'text': "Auto Sell Retry",
                            'name': "Auto Sell Retry : "
                        },
                    },
                    'int': {
                          'SELL_HIGH': {
                            'value': 100,
                            'text': "Sell High",
                            'name': "Sell High : ",
                            'symbol': "%"
                        },
                        'SELL_LOW': {
                            'value': -50,
                            'text': "Sell Low",
                            'name': "Sell Low : ",
                            'symbol': "%"
                        },
                        'SELL_HIGH_AMOUNT': {
                            'value': 50,
                            'text': "Sell High Amount",
                            'name': "Sell High Amount : ",
                            'symbol': "%"
                        },
                        'GAS_DELTA': {
                            'value': 0.001,
                            'text': "Gas Delta",
                            'name': "Sell Gas Price : "
                        },
                        'PIA': {
                            'value': 50,
                            'text': "Price Impact Alert",
                            'name': "Price impact alert : "
                        },
                        'SLIPPAGE': {
                            'value': 10,
                            'text': "Slippage",
                            'name': "Slippage : "
                        },
                    }
                },
            },

            'ETH': {
                'GENERAL': {
                    'WALLETS_CT': {
                        'value': [],
                        'text': "Wallets CT",
                        'name': "Wallets d'adresse du  Copy Trade : "
                    },
                },
                'BUY': {
                    'bool': {
                        'COPY_TRADE': {
                            'value': False,
                            'text': "Off",
                            'name': "Copy Trade Buy : "
                        },
                        'CONFIRM_TRADE': {
                            'value': False,
                            'text': "Confirm Trade",
                            'name': "Confirm Trade Buy : "
                        },
                        'DUPE_BUY': {
                            'value': False,
                            'text': "Dupe Buy",
                            'name': "Duplicate Buy : "
                        },
                        'AUTO_BUY': {
                            'value': False,
                            'text': "Auto Buy",
                            'name': "Auto Buy : "
                        },
                    },
                    'int': {
                        'MIN_MC': {
                            'value': 0,
                            'text': "Min Mc",
                            'name': "Min MCap : "
                        },
                        'MAX_MC': {
                            'value': 0,
                            'text': "Max Mc",
                            'name': "Max MCap : "
                        },
                        'MIN_LIQ': {
                            'value': 0,
                            'text': "Min Liquidity",
                            'name': "Min Liquidity : "
                        },
                        'MAX_LIQ': {
                            'value': 0,
                            'text': "Max Liquidity",
                            'name': "Max Liquidity : "
                        },
                        'MIN_MC_LIQ': {
                            'value': 0,
                            'text': "Min Mc/Liq",
                            'name': "Min MCap/Liq : "
                        },
                        'GAS_DELTA': {
                            'value': 0.001,
                            'text': "Gas Delta",
                            'name': "Buy Gas Delta : "
                        },
                        'PIA': {
                            'value': 25,
                            'text': "Price Impact Alert",
                            'name': "Price impact alert : "
                        },
                        'SLIPPAGE': {
                            'value': 10,
                            'text': "Slippage",
                            'name': "Slippage : "
                        },
                    },
                },
                'SELL': {
                    'bool': {
                        'CONFIRM_TRADE': {
                            'value': False,
                            'text': "Confirm Trade",
                            'name': "Confirm Trade Sell : "
                        },
                        'AUTO_SELL': {
                            'value': False,
                            'text': "Auto Sell",
                            'name': "Auto Sell : "
                        },
                        'TRAILING_SELL': {
                            'value': False,
                            'text': "Trailing Sell",
                            'name': "Trailing Sell : "
                        },
                        'AUTO_SELL_RETRY': {
                            'value': False,
                            'text': "Auto Sell Retry",
                            'name': "Auto Sell Retry : "
                        },
                    },
                    'int': {
                        'SELL_HIGH': {
                            'value': 100,
                            'text': "Sell High",
                            'name': "Sell High : ",
                            'symbol': "%"
                        },
                        'SELL_LOW': {
                            'value': -50,
                            'text': "Sell Low",
                            'name': "Sell Low : ",
                            'symbol': "%"
                        },
                        'SELL_HIGH_AMOUNT': {
                            'value': 50,
                            'text': "Sell High Amount",
                            'name': "Sell High Amount : ",
                            'symbol': "%"
                        },
                        'GAS_DELTA': {
                            'value': 0.001,
                            'text': "Gas Delta",
                            'name': "Sell Gas Price : "
                        },
                        'PIA': {
                            'value': 50,
                            'text': "Price Impact Alert",
                            'name': "Price impact alert : "
                        },
                        'SLIPPAGE': {
                            'value': 10,
                            'text': "Slippage",
                            'name': "Slippage : "
                        },
                    }
                },
            },

            'TRX': {
                'GENERAL': {
                    'WALLETS_CT': {
                        'value': [],
                        'text': "Wallets CT",
                        'name': "Wallets d'adresse du  Copy Trade : "
                    },
                },
                'BUY': {
                    'bool': {
                        'COPY_TRADE': {
                            'value': False,
                            'text': "Off",
                            'name': "Copy Trade Buy : "
                        },
                        'CONFIRM_TRADE': {
                            'value': False,
                            'text': "Confirm Trade",
                            'name': "Confirm Trade Buy : "
                        },
                        'DUPE_BUY': {
                            'value': False,
                            'text': "Dupe Buy",
                            'name': "Duplicate Buy : "
                        },
                        'AUTO_BUY': {
                            'value': False,
                            'text': "Auto Buy",
                            'name': "Auto Buy : "
                        },
                    },
                    'int': {
                        'MIN_MC': {
                            'value': 0,
                            'text': "Min Mc",
                            'name': "Min MCap : "
                        },
                        'MAX_MC': {
                            'value': 0,
                            'text': "Max Mc",
                            'name': "Max MCap : "
                        },
                        'MIN_LIQ': {
                            'value': 0,
                            'text': "Min Liquidity",
                            'name': "Min Liquidity : "
                        },
                        'MAX_LIQ': {
                            'value': 0,
                            'text': "Max Liquidity",
                            'name': "Max Liquidity : "
                        },
                        'MIN_MC_LIQ': {
                            'value': 0,
                            'text': "Min Mc/Liq",
                            'name': "Min MCap/Liq : "
                        },
                        'GAS_DELTA': {
                            'value': 0.001,
                            'text': "Gas Delta",
                            'name': "Buy Gas Delta : "
                        },
                        'PIA': {
                            'value': 25,
                            'text': "Price Impact Alert",
                            'name': "Price impact alert : "
                        },
                        'SLIPPAGE': {
                            'value': 10,
                            'text': "Slippage",
                            'name': "Slippage : "
                        },
                    },
                },
                'SELL': {
                    'bool': {
                        'CONFIRM_TRADE': {
                            'value': False,
                            'text': "Confirm Trade",
                            'name': "Confirm Trade Sell : "
                        },
                        'AUTO_SELL': {
                            'value': False,
                            'text': "Auto Sell",
                            'name': "Auto Sell : "
                        },
                        'TRAILING_SELL': {
                            'value': False,
                            'text': "Trailing Sell",
                            'name': "Trailing Sell : "
                        },
                        'AUTO_SELL_RETRY': {
                            'value': False,
                            'text': "Auto Sell Retry",
                            'name': "Auto Sell Retry : "
                        },
                    },
                    'int': {
                        'SELL_HIGH': {
                            'value': 100,
                            'text': "Sell High",
                            'name': "Sell High : ",
                            'symbol': "%"
                        },
                        'SELL_LOW': {
                            'value': -50,
                            'text': "Sell Low",
                            'name': "Sell Low : ",
                            'symbol': "%"
                        },
                        'SELL_HIGH_AMOUNT': {
                            'value': 50,
                            'text': "Sell High Amount",
                            'name': "Sell High Amount : ",
                            'symbol': "%"
                        },
                        'SELL_LOW_AMOUNT': {
                            'value': 100,
                            'text': "Sell Low Amount",
                            'name': "Sell Low Amount : ",
                            'symbol': "%"
                        },
                        'GAS_DELTA': {
                            'value': 0.001,
                            'text': "Gas Delta",
                            'name': "Sell Gas Price : "
                        },
                        'PIA': {
                            'value': 50,
                            'text': "Price Impact Alert",
                            'name': "Price impact alert : "
                        },
                        'SLIPPAGE': {
                            'value': 10,
                            'text': "Slippage",
                            'name': "Slippage : "
                        },
                    }
                },
            },
        }
        message_ids[update.effective_user.id] = {
            'bot': [],
            'user': []
        }

        print(message_ids)
        user_id = update.effective_user.id
        user_data_json = json.dumps(user_data, indent=4, ensure_ascii=False)
        print(user_data_json)
        await update.message.reply_text(main_menu_message(user_id), reply_markup=main_menu_keyboard())


async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    if user_id in user_data:
        user_data[user_id]['subscribed'] = not user_data[user_id]['subscribed']

    await query.edit_message_text(main_menu_message(user_id), reply_markup=main_menu_keyboard())




# Error handling
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f'Update {update} caused error {context.error}')

def change_value_bool(context: ContextTypes.DEFAULT_TYPE, crypto: str, param_name: str) -> None:
    if param_name in context.user_data['wallets'][crypto]['BUY']['bool']:
        context.user_data['wallets'][crypto]['BUY']['bool'][param_name] = not \
            context.user_data['wallets'][crypto]['bool'][
                param_name]


def change_value_int(context: ContextTypes.DEFAULT_TYPE, crypto: str, param_name: str, value: int) -> None:
    if param_name in context.user_data['wallets'][crypto]['BUY']['int']:
        context.user_data['wallets'][crypto]['BUY']['int'][param_name] = value


def generate_connect_from_wallet_keyboard(crypto) -> InlineKeyboardMarkup:
    keyboard = [
        button_bot_name(),
        [InlineKeyboardButton("🔙 Return", callback_data='show_wallet' + crypto)],
    ]
    return InlineKeyboardMarkup(keyboard)


def generate_from_wallet_keyboard(context: ContextTypes.DEFAULT_TYPE, crypto) -> InlineKeyboardMarkup:
    keyboard = [
        button_bot_name(),
        [InlineKeyboardButton("🔙 Return", callback_data='show_wallet_' + crypto)],
    ]
    return InlineKeyboardMarkup(keyboard)




def extract_user_data(update: Update) -> dict:
    user = update.message.from_user
    return {
        'id': user.id,
        'first_name': user.first_name,
    }

def get_user_data():
    return user_data


if __name__ == '__main__':
    # Replace 'YOUR_TOKEN_HERE' with your bot's token
    TOKEN = os.getenv('TOKEN')

    application = Application.builder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('monitor', monitor))
    application.add_handler(CallbackQueryHandler(main_menu, pattern='main'))
    application.add_handler(CallbackQueryHandler(generate_wallet, pattern='generate_wallet_.*'))
    application.add_handler(CallbackQueryHandler(generate_from_wallet, pattern='generate_from_wallet_*'))

    application.add_handler(CallbackQueryHandler(connect_wallet, pattern='connect_wallet_.*'))
    application.add_handler(CallbackQueryHandler(connect_from_wallet, pattern='connect_from_wallet_.*'))
    application.add_handler(CallbackQueryHandler(disconnect_from_wallet, pattern='disconnect_from_wallet_.*'))

    application.add_handler(CallbackQueryHandler(wallet_menu, pattern='wallet'))
    application.add_handler(CallbackQueryHandler(chain_menu, pattern='toggle_chain_.*'))
    application.add_handler(CallbackQueryHandler(menu_generate_wallet, pattern='menu_generate_wallet_.*'))
    application.add_handler(CallbackQueryHandler(show_wallet, pattern='show_wallet_.*'))

    application.add_handler(CallbackQueryHandler(config_wallet, pattern='config_wallet_.*'))

    # Config Buy  Handler
    application.add_handler(CallbackQueryHandler(config_buy_wallet, pattern='config_buy_wallet_.*'))

    application.add_handler(CallbackQueryHandler(confirm_trade_wallet, pattern='confirm_trade_wallet_.*'))
    application.add_handler(CallbackQueryHandler(dupe_buy_wallet, pattern='dupe_buy_wallet_.*'))
    application.add_handler(CallbackQueryHandler(auto_buy_sell_wallet, pattern='auto_buy_wallet_.*'))

    application.add_handler(CallbackQueryHandler(premium, pattern='premium'))

    application.add_handler(CallbackQueryHandler(ct, pattern='ct'))
    application.add_handler(CallbackQueryHandler(show_copytrade, pattern='show_copytrade_.*'))
    application.add_handler(CallbackQueryHandler(set_copytrade_value, pattern='set_copy_trade_.*'))
    application.add_handler(CallbackQueryHandler(show_faq_text, pattern='faq_.*'))
    application.add_handler(CallbackQueryHandler(faq, pattern='faq'))


    conv_handler_ct_wallet = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_wallet_ct, pattern='add_ct_wallet_.*')],
        states={
            AWAITING_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wallet_address)],
            AWAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wallet_name)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_min_mc = ConversationHandler(
        entry_points=[CallbackQueryHandler(min_mc_wallet, pattern='min_mc_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_min_mc)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_max_mc = ConversationHandler(
        entry_points=[CallbackQueryHandler(max_mc_wallet, pattern='max_mc_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_max_mc)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_min_liq = ConversationHandler(
        entry_points=[CallbackQueryHandler(min_liq_wallet, pattern='min_liq_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_min_liq)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_max_liq = ConversationHandler(
        entry_points=[CallbackQueryHandler(max_liq_wallet, pattern='max_liq_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_max_liq)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_min_mc_liq = ConversationHandler(
        entry_points=[CallbackQueryHandler(min_mc_liq_wallet, pattern='min_mc_liq_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_min_mc_liq)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_gas_delta = ConversationHandler(
        entry_points=[CallbackQueryHandler(gas_delta_wallet, pattern='gas_delta_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_gas_delta)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_pia = ConversationHandler(
        entry_points=[CallbackQueryHandler(pia_wallet, pattern='pia_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pia)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_slippage = ConversationHandler(
        entry_points=[CallbackQueryHandler(slippage_wallet, pattern='slippage_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_slippage)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_sell_high = ConversationHandler(
        entry_points=[CallbackQueryHandler(sell_high_wallet, pattern='sell_high_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sell_high)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_sell_low = ConversationHandler(
        entry_points=[CallbackQueryHandler(sell_low_wallet, pattern='sell_low_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sell_low)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_sell_high_amount = ConversationHandler(
        entry_points=[CallbackQueryHandler(sell_high_amount_wallet, pattern='sell_high_amount_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sell_high_amount)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler_wallet_sell_low_amount = ConversationHandler(
        entry_points=[CallbackQueryHandler(sell_low_amount_wallet, pattern='sell_low_amount_wallet_.*')],
        states={
            AWAITING_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sell_low_amount)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )


    application.add_handler(CallbackQueryHandler(config_sell_wallet, pattern='config_sell_wallet_.*'))
    application.add_handler(conv_handler_wallet_slippage)
    application.add_handler(conv_handler_wallet_pia)
    application.add_handler(conv_handler_wallet_gas_delta)
    application.add_handler(conv_handler_wallet_min_mc_liq)
    application.add_handler(conv_handler_wallet_min_liq)
    application.add_handler(conv_handler_wallet_max_liq)
    application.add_handler(conv_handler_wallet_max_mc)
    application.add_handler(conv_handler_ct_wallet)
    application.add_handler(conv_handler_wallet_min_mc)
    application.add_handler(conv_handler_wallet_sell_low)
    application.add_handler(conv_handler_wallet_sell_high)
    application.add_handler(conv_handler_wallet_sell_high_amount)
    application.add_handler(conv_handler_wallet_sell_low_amount)

    application.add_handler(CallbackQueryHandler(erase_gas_delta_wallet, pattern='erase_gd_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_min_mc_wallet, pattern='erase_min_mc_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_max_mc_wallet, pattern='erase_max_mc_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_min_liq_wallet, pattern='erase_min_liq_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_max_liq_wallet, pattern='erase_max_liq_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_min_mc_liq_wallet, pattern='erase_min_mc_liq_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_pia_wallet, pattern='erase_pia_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_slippage_wallet, pattern='erase_slippage_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_sell_high, pattern='erase_sell_high_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_sell_low, pattern='erase_sell_low_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_sell_high_amount, pattern='erase_sell_high_amount_wallet_.*'))
    application.add_handler(CallbackQueryHandler(erase_sell_low_amount, pattern='erase_sell_low_amount_wallet_.*'))

    application.add_handler(CallbackQueryHandler(trailing_sell_wallet, pattern='trailing_sell_wallet_*'))
    application.add_handler(CallbackQueryHandler(auto_sell, pattern='auto_sell_wallet_*'))
    application.add_handler(CallbackQueryHandler(auto_sell_retry, pattern='auto_sell_retry_wallet_*'))
    # Error handler
    application.add_error_handler(error)

    # Start polling
    application.run_polling(1)
