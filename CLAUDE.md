# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProtoTrader Bot is a Telegram-based trading bot designed for automated cryptocurrency trading. It supports multiple blockchain networks (SOL, ETH, TRX) and provides features for copy trading, wallet management, and automated trading strategies.

## Key Commands

### Running the Bot
```bash
python main.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Environment Setup
- Create a `.env` file with your Telegram bot token: `TOKEN=your_bot_token_here`
- The bot uses python-dotenv to load environment variables
- A `.wallet_key` file is automatically created for wallet encryption (add to .gitignore)

## Architecture Overview

### Main Components

1. **main.py**: Entry point that initializes the Telegram bot application and registers all handlers. Creates initial user data structure with default trading configurations for each supported blockchain.

2. **User Data Structure**: Each user has:
   - Basic info (id, first_name, subscription status)
   - Chain states (SOL, ETH, TRX)
   - Wallet configurations per chain including:
     - Generated wallets (encrypted private keys)
     - Connected wallets (imported, encrypted)
     - Copy trade wallets
     - Buy settings (copy trade, confirm trade, duplicate buy, auto buy)
     - Sell settings (confirm trade, auto sell, trailing sell, auto sell retry)
     - Trading parameters (market cap limits, liquidity limits, gas delta, slippage, price impact alert)

3. **Core Modules**:
   - **wallet_manager.py**: Handles wallet creation, import, and encryption for all chains
   - **trading_engine.py**: Manages trading operations, orders, stop loss/take profit monitoring
   - **trading_commands.py**: Telegram handlers for buy/sell operations
   - **database.py**: Simple JSON-based persistence layer
   - **user_data.py**: Global user data storage and message management

4. **Menu System**:
   - **main_menu.py**: Main menu interface
   - **chain_menu.py**: Chain selection and management
   - **wallets.py**: Wallet management functionality with generation/connection
   - **copy_trade.py**: Copy trading configuration
   - **faq_menu.py**: FAQ interface
   - **monitor.py**: Real-time trade monitoring and quick actions

5. **Trading Features**:
   - Generate new wallets for each chain
   - Import existing wallets via private key
   - Execute buy/sell orders with customizable parameters
   - Automatic stop loss and take profit monitoring
   - Trade monitoring with quick sell options (25%, 50%, 100%)
   - Copy trading configuration

### Key Trading Parameters

- **Market Cap Limits**: MIN_MC, MAX_MC
- **Liquidity Limits**: MIN_LIQ, MAX_LIQ
- **Gas Settings**: GAS_DELTA (default 0.001)
- **Slippage**: Default 10%
- **Price Impact Alert**: Buy default 25%, Sell default 50%
- **Sell Triggers**: SELL_HIGH (100%), SELL_LOW (-50%)

## Security Notes

- Private keys are encrypted using Fernet encryption
- Private key messages are automatically deleted from chat
- Encryption key stored in `.wallet_key` (must be in .gitignore)
- Never log or expose private keys

## Development Notes

- The bot uses telegram.ext library with async/await pattern
- ConversationHandler manages multi-step user interactions
- Trading engine runs async monitoring tasks for stop loss/take profit
- DEX integrations are placeholders - implement actual swap contracts
- Consider implementing proper database (PostgreSQL/MongoDB) for production