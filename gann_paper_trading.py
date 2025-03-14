# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 21:48:17 2025

@author: mahes
"""

# gann_paper_trading.py

import logging
import json
import time
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
import threading
import queue
import argparse

# Import custom modules
from src.tvdata_handler import TVDataHandler
from src.paper_trade_executor import PaperTradeExecutor
from src.gann_calculator import GannCalculator
from src.risk_manager import RiskManager
from src.logger import setup_logger, TradeLogger

class GannPaperTradingSystem:
    """
    Paper trading system using Gann Square of 9 and tvDatafeed
    """
    
    def __init__(self, config_path="config"):
        """
        Initialize the paper trading system
        
        Parameters:
        -----------
        config_path : str
            Path to configuration files
        """
        # Setup logging
        self.logger = setup_logger()
        self.trade_logger = TradeLogger()
        
        # Load configurations
        self.base_path = Path(config_path)
        self.load_configurations()
        
        # Initialize components
        self.initialize_components()
        
        # Signal queue for handling trading signals
        self.signal_queue = queue.Queue()
        
        # Track active symbols and positions
        self.active_symbols = {}
        self.positions = {}
        
        # System state
        self.running = False
        self.last_check_time = {}
    
    def load_configurations(self):
        """Load all configuration files"""
        try:
            # Load API configuration
            api_config_path = self.base_path / "api_config.json"
            with open(api_config_path, 'r') as f:
                self.api_config = json.load(f)
            
            # Load trading configuration
            trading_config_path = self.base_path / "trading_config.json"
            with open(trading_config_path, 'r') as f:
                self.trading_config = json.load(f)
            
            # Load symbols configuration
            symbols_config_path = self.base_path / "symbols.json"
            with open(symbols_config_path, 'r') as f:
                self.symbols_config = json.load(f)
            
            self.logger.info("All configurations loaded successfully")
            
        except FileNotFoundError as e:
            self.logger.error(f"Configuration file not found: {e}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading configurations: {e}")
            raise
    
    def initialize_components(self):
        """Initialize system components"""
        try:
            # Initialize data handler
            self.data_handler = TVDataHandler()
            
            # Initialize Gann calculator
            gann_params = self.trading_config.get('gann_parameters', {})
            self.gann_calculator = GannCalculator(gann_params)
            
            # Initialize paper trade executor
            self.trade_executor = PaperTradeExecutor(
                self.api_config, 
                self.trading_config
            )
            
            # Initialize risk manager
            risk_params = self.trading_config.get('risk_parameters', {})
            self.risk_manager = RiskManager(risk_params)
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise
    
    def start(self):
        """Start the paper trading system"""
        if self.running:
            self.logger.warning("System is already running")
            return
        
        self.running = True
        self.logger.info("Starting Gann Square of 9 Paper Trading System")
        
        # Start signal processor thread
        self.signal_processor_thread = threading.Thread(
            target=self._process_signals,
            daemon=True
        )
        self.signal_processor_thread.start()
        
        # Load active symbols
        self._load_active_symbols()
        
        # Create position tracker file if it doesn't exist
        positions_file = Path("positions.json")
        if positions_file.exists():
            with open(positions_file, 'r') as f:
                self.positions = json.load(f)
        else:
            with open(positions_file, 'w') as f:
                json.dump({}, f)
        
        try:
            # Main trading loop
            while self.running:
                # Check if it's trading time
                if self._is_trading_time():
                    # Process each symbol
                    for symbol_info in self.active_symbols.values():
                        self._process_symbol(symbol_info)
                else:
                    self.logger.info("Outside trading hours, waiting...")
                
                # Wait for the next scan interval
                time.sleep(self.trading_config.get('scan_interval', 60))
                
        except KeyboardInterrupt:
            self.logger.info("System stopped by user")
        except Exception as e:
            self.logger.error(f"Error in main trading loop: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the paper trading system"""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping paper trading system")
        
        # Close positions if configured to do so
        if self.trading_config.get('close_positions_on_exit', False):
            self._close_all_positions("System shutdown")
        
        # Save positions
        self._save_positions()
        
        # Wait for signal processor to complete
        if hasattr(self, 'signal_processor_thread') and self.signal_processor_thread.is_alive():
            self.signal_queue.put(None)  # Signal to exit
            self.signal_processor_thread.join(timeout=5)
        
        self.logger.info("Paper trading system stopped")
    
    def _load_active_symbols(self):
        """Load active symbols from configuration"""
        for symbol_info in self.symbols_config.get('symbols', []):
            symbol = symbol_info.get('symbol')
            if symbol:
                # Add default fields if missing
                if 'timeframe' not in symbol_info:
                    symbol_info['timeframe'] = self.trading_config.get('default_timeframe', '1h')
                if 'exchange' not in symbol_info:
                    symbol_info['exchange'] = self.trading_config.get('default_exchange', 'NSE')
                
                # Store in active symbols dictionary
                self.active_symbols[symbol] = symbol_info
        
        self.logger.info(f"Loaded {len(self.active_symbols)} active symbols")
    
    def _is_trading_time(self):
        """Check if current time is within trading hours"""
        trading_hours = self.trading_config.get('trading_hours', {})
        
        if not trading_hours:
            # Default trading hours (9:15 AM to 3:30 PM IST, weekdays only)
            return self.data_handler.get_exchange_info().get('is_open', False)
        
        # Get current time
        now = datetime.now()
        
        # Check if it's a weekday (0=Monday, 4=Friday)
        if now.weekday() > 4:
            return False
        
        # Parse trading hours
        start_time = datetime.strptime(trading_hours.get('start', '09:15'), "%H:%M").time()
        end_time = datetime.strptime(trading_hours.get('end', '15:30'), "%H:%M").time()
        
        # Check if within trading hours
        return start_time <= now.time() <= end_time
    
    def _process_symbol(self, symbol_info):
        """
        Process a symbol for trading signals
        
        Parameters:
        -----------
        symbol_info : dict
            Symbol information
        """
        symbol = symbol_info.get('symbol')
        exchange = symbol_info.get('exchange', 'NSE')
        timeframe = symbol_info.get('timeframe', '1h')
        symbol_type = symbol_info.get('type', 'equity')
        
        # Check if it's time to process this symbol based on timeframe
        if not self._should_process_symbol(symbol, timeframe):
            return
        
        self.logger.info(f"Processing {symbol} ({timeframe})")
        
        try:
            # Get previous candle data
            prev_candle = self.data_handler.get_previous_candle(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe
            )
            
            if not prev_candle:
                self.logger.warning(f"Could not get previous candle data for {symbol}")
                return
            
            # Get current price
            current_price = self.data_handler.get_current_price(symbol, exchange)
            
            if not current_price:
                self.logger.warning(f"Could not get current price for {symbol}")
                return
            
            # Calculate Gann levels using previous candle close
            prev_close = prev_candle['close']
            gann_results = self.gann_calculator.calculate(prev_close)
            
            if not gann_results:
                self.logger.warning(f"Gann calculation failed for {symbol}")
                return
            
            # Check for trading signals
            signal = self._check_for_signal(
                symbol=symbol,
                symbol_type=symbol_type,
                gann_results=gann_results,
                current_price=current_price
            )
            
            if signal:
                # Add symbol info to signal
                signal['symbol_info'] = symbol_info
                
                # Queue the signal for processing
                self.signal_queue.put(signal)
                
                # Log the signal
                self.trade_logger.log_signal(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type=signal['action'],
                    price=current_price,
                    gann_level=signal.get('level', 0)
                )
            else:
                self.logger.info(f"No trading signal for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error processing {symbol}: {e}")
    
    def _should_process_symbol(self, symbol, timeframe):
        """
        Check if it's time to process a symbol based on its timeframe
        
        Parameters:
        -----------
        symbol : str
            Symbol name
        timeframe : str
            Timeframe (1m, 5m, 15m, 1h, etc.)
            
        Returns:
        --------
        bool
            True if the symbol should be processed
        """
        now = datetime.now()
        key = f"{symbol}_{timeframe}"
        
        # If no previous check time, process now
        if key not in self.last_check_time:
            self.last_check_time[key] = now
            return True
        
        # Get interval in seconds based on timeframe
        interval_seconds = self._get_interval_seconds(timeframe)
        
        # Minimum processing interval is 1 minute
        min_interval = 60
        
        # For higher timeframes, we'll check more frequently
        if interval_seconds > 300:  # 5 minutes or higher
            check_interval = min(interval_seconds // 5, 300)  # At most every 5 minutes
        else:
            check_interval = max(interval_seconds, min_interval)
        
        # Check if enough time has elapsed
        time_diff = (now - self.last_check_time[key]).total_seconds()
        
        if time_diff >= check_interval:
            self.last_check_time[key] = now
            return True
        
        return False
    
    def _get_interval_seconds(self, timeframe):
        """
        Convert timeframe to seconds
        
        Parameters:
        -----------
        timeframe : str
            Timeframe (1m, 5m, 15m, 1h, etc.)
            
        Returns:
        --------
        int
            Interval in seconds
        """
        timeframe = timeframe.lower()
        
        if timeframe.endswith('m'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 3600
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 86400
        elif timeframe.endswith('w'):
            return int(timeframe[:-1]) * 604800
        else:
            # Default to 1 hour
            return 3600
    
    def _check_for_signal(self, symbol, symbol_type, gann_results, current_price):
        """
        Check if there's a trading signal based on Gann levels
        
        Parameters:
        -----------
        symbol : str
            Symbol name
        symbol_type : str
            Symbol type (equity or index)
        gann_results : dict
            Gann calculation results
        current_price : float
            Current market price
            
        Returns:
        --------
        dict or None
            Signal details if a signal is generated, None otherwise
        """
        buy_above = gann_results.get('buy_above')
        sell_below = gann_results.get('sell_below')
        
        # Skip if we can't determine levels
        if not buy_above or not sell_below:
            return None
        
        # Check for existing positions to avoid duplicate signals
        if self._has_open_position(symbol):
            return None
        
        # BUY signal
        if current_price > buy_above:
            self.logger.info(f"BUY signal: {symbol} price {current_price} > buy_above {buy_above}")
            
            # Based on symbol type, determine action
            if symbol_type == 'equity':
                # For equity: Buy stock and CE option
                return {
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': current_price,
                    'level': buy_above,
                    'target': gann_results.get('buy_targets', [])[0] if gann_results.get('buy_targets') else None,
                    'stop_loss': gann_results.get('stoploss_long'),
                    'timestamp': datetime.now().isoformat()
                }
            elif symbol_type == 'index':
                # For index: Buy CE option
                return {
                    'symbol': symbol,
                    'action': 'BUY_CE',
                    'price': current_price,
                    'level': buy_above,
                    'target': gann_results.get('buy_targets', [])[0] if gann_results.get('buy_targets') else None,
                    'stop_loss': gann_results.get('stoploss_long'),
                    'timestamp': datetime.now().isoformat()
                }
        
        # SELL signal (for buying PE options)
        if current_price < sell_below:
            self.logger.info(f"SELL signal: {symbol} price {current_price} < sell_below {sell_below}")
            
            if symbol_type == 'equity':
                # For equity: Buy PE option
                return {
                    'symbol': symbol,
                    'action': 'BUY_PE',
                    'price': current_price,
                    'level': sell_below,
                    'target': gann_results.get('sell_targets', [])[0] if gann_results.get('sell_targets') else None,
                    'stop_loss': gann_results.get('stoploss_short'),
                    'timestamp': datetime.now().isoformat()
                }
            elif symbol_type == 'index':
                # For index: Buy PE option
                return {
                    'symbol': symbol,
                    'action': 'BUY_PE',
                    'price': current_price,
                    'level': sell_below,
                    'target': gann_results.get('sell_targets', [])[0] if gann_results.get('sell_targets') else None,
                    'stop_loss': gann_results.get('stoploss_short'),
                    'timestamp': datetime.now().isoformat()
                }
        
        return None
    
    def _process_signals(self):
        """Process trading signals from the queue"""
        while self.running:
            try:
                # Get signal from queue (with timeout)
                signal = self.signal_queue.get(timeout=1)
                
                # None is the signal to exit
                if signal is None:
                    break
                
                # Process the signal
                self._execute_signal(signal)
                
                # Mark task as done
                self.signal_queue.task_done()
                
            except queue.Empty:
                # Queue is empty, continue waiting
                continue
            except Exception as e:
                self.logger.error(f"Error processing signal: {e}")
    
    def _execute_signal(self, signal):
        """
        Execute a trading signal
        
        Parameters:
        -----------
        signal : dict
            Signal details
        """
        symbol = signal.get('symbol')
        action = signal.get('action')
        price = signal.get('price')
        symbol_info = signal.get('symbol_info', {})
        
        self.logger.info(f"Executing signal: {symbol} {action} at {price}")
        
        try:
            # Calculate position size based on risk
            account_info = {"balance": 1000000}  # Simulated account balance
            stop_loss = signal.get('stop_loss')
            
            position_size = self.risk_manager.calculate_position_size(
                account_balance=account_info["balance"],
                entry_price=price,
                stop_loss=stop_loss
            )
            
            # Equity order execution
            if action == 'BUY' and symbol_info.get('type') == 'equity':
                # For equity: Buy stock
                stock_order = self._place_stock_order(symbol, symbol_info, position_size, price)
                
                # Also buy CE option
                option_order = self._place_option_order(
                    symbol=symbol,
                    symbol_info=symbol_info,
                    option_type='CE',
                    price=price
                )
                
                # Track the position
                if stock_order and stock_order.get('status') == 'success':
                    position_id = stock_order.get('order_id')
                    position = {
                        'id': position_id,
                        'symbol': symbol,
                        'type': 'EQUITY_LONG',
                        'entry_price': price,
                        'quantity': position_size,
                        'stop_loss': stop_loss,
                        'target': signal.get('target'),
                        'option_order_id': option_order.get('order_id') if option_order else None,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'OPEN'
                    }
                    
                    self.positions[position_id] = position
                    self._save_positions()
                    
                    self.logger.info(f"Position opened: {position_id}")
            
            # Option order execution for indexes or PE signals
            elif action in ['BUY_CE', 'BUY_PE']:
                option_type = 'CE' if action == 'BUY_CE' else 'PE'
                
                option_order = self._place_option_order(
                    symbol=symbol,
                    symbol_info=symbol_info,
                    option_type=option_type,
                    price=price
                )
                
                # Track the position
                if option_order and option_order.get('status') == 'success':
                    position_id = option_order.get('order_id')
                    position = {
                        'id': position_id,
                        'symbol': symbol,
                        'type': f'OPTION_{option_type}',
                        'entry_price': price,
                        'quantity': symbol_info.get('option_lot_size', 1),
                        'stop_loss': stop_loss,
                        'target': signal.get('target'),
                        'timestamp': datetime.now().isoformat(),
                        'status': 'OPEN'
                    }
                    
                    self.positions[position_id] = position
                    self._save_positions()
                    
                    self.logger.info(f"Option position opened: {position_id}")
            
        except Exception as e:
            self.logger.error(f"Error executing signal for {symbol}: {e}")
    
    def _place_stock_order(self, symbol, symbol_info, quantity, price):
        """
        Place a stock order
        
        Parameters:
        -----------
        symbol : str
            Symbol name
        symbol_info : dict
            Symbol information
        quantity : int
            Order quantity
        price : float
            Current price
            
        Returns:
        --------
        dict
            Order result
        """
        exchange = symbol_info.get('exchange', 'NSE')
        
        # Prepare order parameters
        params = {
            'symbol': symbol,
            'action': 'BUY',
            'quantity': quantity,
            'price': price
        }
        
        # Send webhook order
        return self.trade_executor.send_webhook_order(
            strategy_id='GANN_STOCK',
            action='BUY',
            parameters=params
        )
    
    def _place_option_order(self, symbol, symbol_info, option_type, price):
        """
        Place an option order
        
        Parameters:
        -----------
        symbol : str
            Symbol name
        symbol_info : dict
            Symbol information
        option_type : str
            Option type (CE or PE)
        price : float
            Current price
            
        Returns:
        --------
        dict
            Order result
        """
        exchange = symbol_info.get('exchange', 'NSE')
        option_lot_size = symbol_info.get('option_lot_size', 1)
        
        # Determine appropriate strike price
        if option_type == 'CE':
            # For CE, round down to nearest strike
            strike_price = self._get_atm_strike(symbol, price, symbol_info, round_up=False)
        else:
            # For PE, round up to nearest strike
            strike_price = self._get_atm_strike(symbol, price, symbol_info, round_up=True)
        
        # Get current expiry
        expiry = self._get_current_expiry(symbol_info.get('type', 'equity'))
        
        # Construct option symbol (format depends on broker)
        option_symbol = f"{symbol}{expiry}{strike_price}{option_type}"
        
        # Log option order details
        self.logger.info(f"Placing option order: {option_symbol}, Quantity: {option_lot_size}")
        
        # Prepare order parameters
        params = {
            'symbol': option_symbol,
            'action': 'BUY',
            'quantity': option_lot_size,
            'price': price,
            'product': 'NRML',
            'exchange': 'NFO'
        }
        
        # Send webhook order
        return self.trade_executor.send_webhook_order(
            strategy_id='GANN_OPTION',
            action='BUY',
            parameters=params
        )
    
    def _get_atm_strike(self, symbol, current_price, symbol_info, round_up=False):
        """
        Get the at-the-money strike price
        
        Parameters:
        -----------
        symbol : str
            Symbol name
        current_price : float
            Current price
        symbol_info : dict
            Symbol information
        round_up : bool
            Whether to round up (True) or down (False)
            
        Returns:
        --------
        float
            Strike price
        """
        # Get strike interval based on symbol
        if symbol in ['NIFTY', 'NIFTY50']:
            interval = 50
        elif symbol in ['BANKNIFTY', 'NIFTYBANK']:
            interval = 100
        elif symbol in ['FINNIFTY']:
            interval = 50
        else:
            # For stocks, use percentage of price
            price_percent = current_price * 0.01
            
            if price_percent < 5:
                interval = 5
            elif price_percent < 10:
                interval = 10
            elif price_percent < 25:
                interval = 25
            elif price_percent < 50:
                interval = 50
            else:
                interval = 100
        
        # Calculate nearest strike
        if round_up:
            return ceil(current_price / interval) * interval
        else:
            return floor(current_price / interval) * interval
    
    def _get_current_expiry(self, symbol_type):
        """
        Get the current expiry date string
        
        Parameters:
        -----------
        symbol_type : str
            Symbol type (equity or index)
            
        Returns:
        --------
        str
            Expiry date string in the format required by the broker
        """
        now = datetime.now()
        
        if symbol_type == 'index':
            # For indexes, get the nearest weekly expiry (usually Thursday)
            days_to_thursday = (3 - now.weekday()) % 7
            
            # If today is Thursday and it's past market close, get next week
            if days_to_thursday == 0 and now.hour >= 15:
                days_to_thursday = 7
            
            expiry_date = now + timedelta(days=days_to_thursday)
        else:
            # For equities, get the monthly expiry (last Thursday of the month)
            # This is simplified - in a production system you'd need more robust logic
            
            # Get the last day of the current month
            if now.month == 12:
                last_day = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
            
            # Find the last Thursday
            days_to_subtract = (last_day.weekday() - 3) % 7
            last_thursday = last_day - timedelta(days=days_to_subtract)
            
            # If the last Thursday has passed, use the last Thursday of next month
            if last_thursday < now:
                if now.month == 12:
                    last_day = datetime(now.year + 1, 2, 1) - timedelta(days=1)
                else:
                    last_day = datetime(now.year, now.month + 2, 1) - timedelta(days=1)
                
                days_to_subtract = (last_day.weekday() - 3) % 7
                last_thursday = last_day - timedelta(days=days_to_subtract)
            
            expiry_date = last_thursday
        
        # Format the expiry date according to broker requirements
        # Example format: "23JUN" or "29JUN23" or "29JUN2023" - adjust as needed
        return expiry_date.strftime("%d%b").upper()
    
    def _has_open_position(self, symbol):
        """
        Check if there's already an open position for a symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol name
            
        Returns:
        --------
        bool
            True if an open position exists
        """
        for position_id, position in self.positions.items():
            if position.get('symbol') == symbol and position.get('status') == 'OPEN':
                return True
        
        return False
    
    def _monitor_positions(self):
        """Monitor open positions for exit conditions"""
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            if position.get('status') != 'OPEN':
                continue
            
            symbol = position.get('symbol')
            symbol_info = self.active_symbols.get(symbol, {})
            
            try:
                # Get current price
                current_price = self.data_handler.get_current_price(
                    symbol=symbol,
                    exchange=symbol_info.get('exchange', 'NSE')
                )
                
                if not current_price:
                    continue
                
                # Check stop loss
                stop_loss = position.get('stop_loss')
                if stop_loss:
                    if (position.get('type') in ['EQUITY_LONG', 'OPTION_CE'] and current_price <= stop_loss) or \
                       (position.get('type') == 'OPTION_PE' and current_price >= stop_loss):
                        self.logger.info(f"Stop loss triggered for {position_id}: {symbol} at {current_price}")
                        positions_to_close.append((position_id, "Stop Loss", current_price))
                        continue
                
                # Check target
                target = position.get('target')
                if target:
                    if (position.get('type') in ['EQUITY_LONG', 'OPTION_CE'] and current_price >= target) or \
                       (position.get('type') == 'OPTION_PE' and current_price <= target):
                        self.logger.info(f"Target reached for {position_id}: {symbol} at {current_price}")
                        positions_to_close.append((position_id, "Target", current_price))
                        continue
                
            except Exception as e:
                self.logger.error(f"Error monitoring position {position_id}: {e}")
        
        # Close positions that met exit conditions
        for position_id, reason, price in positions_to_close:
            self._close_position(position_id, reason, price)
    
    def _close_position(self, position_id, reason, price=None):
        """
        Close a position
        
        Parameters:
        -----------
        position_id : str
            Position ID
        reason : str
            Reason for closing
        price : float
            Exit price (optional)
        """
        if position_id not in self.positions:
            self.logger.warning(f"Position not found: {position_id}")
            return
        
        position = self.positions[position_id]
        
        if position.get('status') != 'OPEN':
            self.logger.warning(f"Position {position_id} is not open")
            return
        
        symbol = position.get('symbol')
        position_type = position.get('type')
        
        # Get current price if not provided
        if price is None:
            symbol_info = self.active_symbols.get(symbol, {})
            try:
                price = self.data_handler.get_current_price(
                    symbol=symbol,
                    exchange=symbol_info.get('exchange', 'NSE')
                )
            except Exception as e:
                self.logger.error(f"Error getting price for {symbol}: {e}")
                price = position.get('entry_price')  # Fallback to entry price
        
        # Close the position
        self.logger.info(f"Closing position {position_id}: {symbol} ({position_type}) at {price}, reason: {reason}")
        
        # For equity positions, also close associated option positions
        if position_type == 'EQUITY_LONG' and position.get('option_order_id'):
            option_order_id = position.get('option_order_id')
            self.trade_executor.close_position(option_order_id, price, reason)
        
        # Close the main position
        result = self.trade_executor.close_position(position_id, price, reason)
        
        if result and result.get('status') == 'success':
            # Update position status
            position['status'] = 'CLOSED'
            position['exit_price'] = price
            position['exit_reason'] = reason
            position['exit_time'] = datetime.now().isoformat()
            
            # Calculate P&L
            entry_price = position.get('entry_price', 0)
            quantity = position.get('quantity', 0)
            
            if position_type in ['EQUITY_LONG', 'OPTION_CE']:
                pnl = (price - entry_price) * quantity
            else:  # OPTION_PE
                pnl = (entry_price - price) * quantity
            
            position['pnl'] = pnl
            
            # Save positions
            self._save_positions()
            
            # Log the trade
            self.trade_logger.log_position(
                symbol=symbol,
                action="LONG" if position_type in ['EQUITY_LONG', 'OPTION_CE'] else "SHORT",
                quantity=quantity,
                entry_price=entry_price,
                exit_price=price,
                pnl=pnl,
                exit_reason=reason
            )
            
            self.logger.info(f"Position {position_id} closed with P&L: {pnl}")
    
    def _close_all_positions(self, reason):
        """
        Close all open positions
        
        Parameters:
        -----------
        reason : str
            Reason for closing
        """
        open_positions = [pos_id for pos_id, pos in self.positions.items() 
                          if pos.get('status') == 'OPEN']
        
        for position_id in open_positions:
            self._close_position(position_id, reason)
        
        self.logger.info(f"Closed all positions ({len(open_positions)}) due to: {reason}")
    
    def _save_positions(self):
        """Save positions to file"""
        try:
            with open("positions.json", 'w') as f:
                json.dump(self.positions, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving positions: {e}")
    
    def get_performance_summary(self):
        """
        Get a performance summary of trading activity
        
        Returns:
        --------
        dict
            Performance metrics
        """
        closed_positions = [pos for pos in self.positions.values() 
                           if pos.get('status') == 'CLOSED']
        
        if not closed_positions:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "total_pnl": 0
            }
        
        # Calculate metrics
        total_trades = len(closed_positions)
        winning_trades = [pos for pos in closed_positions if pos.get('pnl', 0) > 0]
        losing_trades = [pos for pos in closed_positions if pos.get('pnl', 0) <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        total_profit = sum(pos.get('pnl', 0) for pos in winning_trades)
        total_loss = abs(sum(pos.get('pnl', 0) for pos in losing_trades))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        total_pnl = sum(pos.get('pnl', 0) for pos in closed_positions)
        
        return {
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl
        }

# Add necessary imports at the top that were omitted
from math import ceil, floor
from datetime import datetime, timedelta

# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gann Square of 9 Paper Trading System")
    parser.add_argument("--config", default="config", help="Path to configuration directory")
    args = parser.parse_args()
    
    # Initialize and start the system
    system = GannPaperTradingSystem(args.config)
    
    try:
        system.start()
    except KeyboardInterrupt:
        print("Stopping system...")
    finally:
        system.stop()