<<<<<<< HEAD
# Gann Square of 9 Trading System

A trading system that implements W.D. Gann's Square of 9 methodology for trading stocks, indices, and commodities.

## Features

- Uses TradingView data for real-time analysis
- Implements original Gann Square of 9 calculations
- Supports both paper trading and live trading
- Integrates with AlgoMojo multi-broker API
- Follows specific trading rules for different asset types

## Setup

1. Install required packages:
    pip install -r requirements.txt
2. Configure your API settings in `config/api_config.json`
3. Customize trading parameters in `config/trading_config.json`
4. Define symbols to trade in `config/symbols.json`

## Usage

For paper trading:
    python gann_trading_system.py --mode paper
    
For live trading:
    python gann_trading_system.py --mode live
    
## Project Structure

- `src/`: Source code modules
- `config/`: Configuration files
- `logs/`: System and trade logs
- `strategy_templates/`: Templates for paper trading
- `orders/`: Order tracking files
=======
# gann_algomojo
>>>>>>> d73d37f4c7d5b4a0054f5d956ff3051eee97764f
