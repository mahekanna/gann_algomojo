# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 21:21:20 2025

@author: mahes
"""

# main.py - Entry point for the Gann Square of 9 Trading System

import json
import logging
import time
from pathlib import Path
from datetime import datetime

from src.data_handler import DataHandler
from src.gann_calculator import GannCalculator
from src.trade_executor import TradeExecutor
from src.risk_manager import RiskManager
from src.logger import setup_logger

def load_config(config_path):
    """Load configuration files"""
    with open(config_path, 'r') as f:
        return json.load(f)

def main():
    # Setup logging
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("Starting Gann Square of 9 Trading System")
    
    # Load configurations
    try:
        base_path = Path(__file__).parent
        api_config = load_config(base_path / 'config' / 'api_config.json')
        trading_config = load_config(base_path / 'config' / 'trading_config.json')
        symbols_config = load_config(base_path / 'config' / 'symbols.json')
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return
    
    # Initialize components
    try:
        data_handler = DataHandler(api_config)
        gann_calculator = GannCalculator(trading_config['gann_parameters'])
        trade_executor = TradeExecutor(api_config, trading_config)
        risk_manager = RiskManager(trading_config['risk_parameters'])
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        return
    
    # Main trading loop
    try:
        while True:
            current_time = datetime.now()
            trading_hours = trading_config.get('trading_hours', {})
            
            # Check if within trading hours
            if not is_trading_time(current_time, trading_hours):
                logger.info("Outside trading hours. Waiting...")
                time.sleep(60)  # Sleep for a minute
                continue
            
            # Process each symbol
            for symbol_info in symbols_config['symbols']:
                process_symbol(symbol_info, data_handler, gann_calculator, 
                               trade_executor, risk_manager, trading_config)
            
            # Wait for next iteration
            time.sleep(trading_config.get('scan_interval', 300))
    except KeyboardInterrupt:
        logger.info("Trading system stopped by user")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        # Cleanup and close positions if needed
        if 'close_positions_on_exit' in trading_config and trading_config['close_positions_on_exit']:
            logger.info("Closing all positions before exit")
            trade_executor.close_all_positions()
        logger.info("Trading system shutdown complete")

def is_trading_time(current_time, trading_hours):
    """Check if current time is within trading hours"""
    weekday = current_time.weekday()
    
    # Weekend check (5=Saturday, 6=Sunday)
    if weekday in [5, 6]:
        return False
    
    start_time = datetime.strptime(trading_hours['start'], "%H:%M").time()
    end_time = datetime.strptime(trading_hours['end'], "%H:%M").time()
    
    return start_time <= current_time.time() <= end_time

def process_symbol(symbol_info, data_handler, gann_calculator, trade_executor, risk_manager, trading_config):
    """Process a single symbol for trading signals"""
    logger = logging.getLogger(__name__)
    
    symbol = symbol_info['symbol']
    timeframe = symbol_info.get('timeframe', trading_config['default_timeframe'])
    symbol_type = symbol_info['type']  # 'equity' or 'index'
    
    logger.info(f"Processing {symbol} ({symbol_type}) on {timeframe} timeframe")
    
    try:
        # Fetch latest data
        price_data = data_handler.get_historical_data(symbol, timeframe)
        if price_data is None or len(price_data) < 2:
            logger.warning(f"Insufficient data for {symbol}")
            return
        
        # Get the previous candle close price
        prev_close = price_data.iloc[-2]['close']
        current_price = price_data.iloc[-1]['close']
        
        # Calculate Gann levels
        gann_results = gann_calculator.calculate(prev_close)
        
        # Check for signals
        signal = check_for_signal(gann_results, current_price, symbol_type)
        
        if signal:
            # Calculate position size
            account_info = trade_executor.get_account_info()
            position_size = risk_manager.calculate_position_size(
                account_info['balance'],
                current_price,
                gann_results['stoploss_long'] if signal['action'] == 'BUY' else gann_results['stoploss_short']
            )
            
            # Execute the trade
            if position_size > 0:
                execute_trade(signal, symbol_info, position_size, gann_results, trade_executor)
            else:
                logger.warning(f"Position size calculation returned 0 for {symbol}")
        else:
            logger.info(f"No trading signal for {symbol}")
            
    except Exception as e:
        logger.error(f"Error processing {symbol}: {e}")

def check_for_signal(gann_results, current_price, symbol_type):
    """Check if there's a trading signal based on Gann levels and price"""
    logger = logging.getLogger(__name__)
    
    buy_above = gann_results.get('buy_above')
    sell_below = gann_results.get('sell_below')
    
    if buy_above and current_price > buy_above:
        # For equity and index, we can generate BUY signals
        logger.info(f"BUY signal: current price {current_price} > buy_above {buy_above}")
        return {
            'action': 'BUY',
            'price': current_price,
            'target': gann_results.get('buy_targets', [])[0] if gann_results.get('buy_targets') else None,
            'stop_loss': gann_results.get('stoploss_long')
        }
    
    if sell_below and current_price < sell_below:
        # For equity, we only buy PE options on sell signals
        # For index, we only generate buy signals
        if symbol_type == 'equity':
            logger.info(f"SELL signal for equity (buy PE): current price {current_price} < sell_below {sell_below}")
            return {
                'action': 'BUY_PE',  # Special action to buy PE options
                'price': current_price,
                'target': gann_results.get('sell_targets', [])[0] if gann_results.get('sell_targets') else None,
                'stop_loss': gann_results.get('stoploss_short')
            }
        
    return None

def execute_trade(signal, symbol_info, position_size, gann_results, trade_executor):
    """Execute the trade based on the signal and trading rules"""
    logger = logging.getLogger(__name__)
    
    symbol = symbol_info['symbol']
    symbol_type = symbol_info['type']
    
    if signal['action'] == 'BUY':
        if symbol_type == 'equity':
            # For equity: Buy the stock
            logger.info(f"Executing BUY order for {symbol}, quantity: {position_size}")
            order_result = trade_executor.place_order(
                symbol=symbol,
                action="BUY",
                quantity=position_size,
                price_type="MARKET"
            )
            
            if order_result and order_result.get('status') == 'success':
                # Also buy the CE option
                option_symbol = get_atm_option_symbol(symbol, "CE", trade_executor)
                logger.info(f"Executing BUY order for {option_symbol} (CE option)")
                trade_executor.place_order(
                    symbol=option_symbol,
                    action="BUY",
                    quantity=symbol_info.get('option_lot_size', 1),
                    price_type="MARKET"
                )
        
        elif symbol_type == 'index':
            # For index: Only buy CE option
            option_symbol = get_atm_option_symbol(symbol, "CE", trade_executor)
            logger.info(f"Executing BUY order for {option_symbol} (CE option for index)")
            trade_executor.place_order(
                symbol=option_symbol,
                action="BUY",
                quantity=symbol_info.get('option_lot_size', 1),
                price_type="MARKET"
            )
    
    elif signal['action'] == 'BUY_PE' and symbol_type == 'equity':
        # For equity sell signal: Buy PE option
        option_symbol = get_atm_option_symbol(symbol, "PE", trade_executor)
        logger.info(f"Executing BUY order for {option_symbol} (PE option)")
        trade_executor.place_order(
            symbol=option_symbol,
            action="BUY",
            quantity=symbol_info.get('option_lot_size', 1),
            price_type="MARKET"
        )

def get_atm_option_symbol(symbol, option_type, trade_executor):
    """Get the at-the-money option symbol for a given underlying"""
    # In a real implementation, this would fetch option chain data
    # and determine the correct ATM option symbol
    # This is a simplified placeholder
    current_price = trade_executor.get_current_price(symbol)
    strike = round(current_price / 10) * 10  # Round to nearest 10
    # Format would depend on exchange requirements
    # Example format: NIFTY22JUN16000CE
    return f"{symbol}CURRENT_EXPIRY{strike}{option_type}"

if __name__ == "__main__":
    main()