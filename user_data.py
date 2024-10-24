user_data = {}
message_ids = {}


def get_user_data():
    return user_data

async def reply_message_conv(update, user_id, text):
    message = await update.message.reply_text(text)
    # Store the message ID to delete later
    if user_id not in message_ids:
        message_ids[user_id] = {'bot': [], 'user': []}
    message_ids[user_id]['user'].append(update.message.message_id)
    message_ids[user_id]['bot'].append(message.message_id)

async def delete_conv(update, user_id):
    if user_id in message_ids:
        for msg_id in message_ids[user_id]['bot']:
            try:
                await update.message.chat.delete_message(msg_id)
            except Exception as e:
                print(f"Failed to delete bot message {msg_id}: {e}")
        for msg_id in message_ids[user_id]['user']:
            try:
                await update.message.chat.delete_message(msg_id)
            except Exception as e:
                print(f"Failed to delete user message {msg_id}: {e}")


def init_user_data(user_id,first_name):
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
                    'TRAILING': {
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
                        'name': "Slippage : ",
                        'symbol': "%"
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
                    'TRAILING': {
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
                        'name': "Slippage : ",
                        'symbol': "%"
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
                        'name': "Slippage : ",
                        'symbol': "%"
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
                    'TRAILING': {
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
                        'name': "Slippage : ",
                        'symbol': "%"
                    },
                }
            },
        },
    }