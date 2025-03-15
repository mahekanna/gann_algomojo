# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 23:33:09 2025

@author: mahes
"""

# -*- coding: utf-8 -*-
"""
Gann Square of 9 Trading Bot

This script integrates all components to create an automated trading system
based on W.D. Gann's Square of 9 methodology.
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
import threading
import queue
import signal
import math
import timedelta

# Import custom modules
from src.tvdata_handler import TVDataHandler
from src.gann_calculator import GannCalculator
from src.risk_manager import RiskManager
from src.symbol_registry import SymbolRegistry
from src.algomojo_api import AlgoMojoAPI

# Setup logging
def setup_logger(debug=False):
    """Setup and return a logger"""
    log_level = logging.DEBUG if debug else logging.INFO
    
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    log_dir = Path("logs")
    if not log_dir.exists():
        log_dir.mkdir(parents=True)
    
    log_file = log_dir / f"gann_trading_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class GannTradingBot:
    """
    Gann Square of 9 Trading Bot with support for both paper and live trading
    """
    
    def __init__(self, config_path="config", mode="paper", debug=False):
        """
        Initialize the trading bot
        
        Parameters:
        -----------
        config_path : str
            Path to configuration files
        mode : str
            Trading mode ("paper" or "live")
        debug : bool
            Enable debug logging
        """
        # Setup logging
        self.logger = setup_logger(debug)
        
        # Set trading mode
        self.mode = mode.lower()
        if self.mode not in ["paper", "live"]:
            self.logger.warning(f"Invalid mode: {mode}, defaulting to paper trading")
            self.mode = "paper"
        
        self.logger.info(f"Initializing Gann Trading Bot in {self.mode.upper()} mode")
        
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
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
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
            
            # Override paper trading setting based on mode
            self.trading_config['paper_trading'] = (self.mode == "paper")
            
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
            # Initialize TV data handler
            self.data_handler = TVDataHandler(self.base_path)
            
            # Initialize Gann calculator
            gann_params = self.trading_config.get('gann_parameters', {})
            self.gann_calculator = GannCalculator(gann_params)
            
            # Initialize AlgoMojo API client
            self.api_client = AlgoMojoAPI(
                api_key=self.api_config.get('api_key', ''),
                api_secret=self.api_config.get('api_secret', ''),
                broker_code=self.api_config.get('broker_code', 'ab'),
                base_url=self.api_config.get('api_base_url', 'https://amapi.algomojo.com/v1')
            )
            
            # Initialize risk manager
            risk_params = self.trading_config.get('risk_parameters', {})
            self.risk_manager = RiskManager(risk_params)
            
            # Initialize symbol registry
            self.symbol_registry = SymbolRegistry(self.base_path)
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise
    
    def start(self):
        """Start the trading bot"""
        if self.running:
            self.logger.warning("Bot is already running")
            return
        
        self.running = True
        self.logger.info(f"Starting Gann Square of 9 Trading Bot in {self.mode.upper()} mode")
        
        # Start signal processor thread
        self.signal_processor_thread = threading.Thread(
            target=self._process_signals,
            daemon=True
        )
        self.signal_processor_thread.start()
        
        # Start position monitor thread
        self.position_monitor_thread = threading.Thread(
            target=self._monitor_positions_thread,
            daemon=True
        )
        self.position_monitor_thread.start()
        
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
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Error in main trading loop: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the trading bot"""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping trading bot")
        
        # Close positions if configured to do so
        if self.trading_config.get('close_positions_on_exit', False):
            self._close_all_positions("System shutdown")
        
        # Save positions
        self._save_positions()
        
        # Wait for threads to complete
        if hasattr(self, 'signal_processor_thread') and self.signal_processor_thread.is_alive():
            self.signal_queue.put(None)  # Signal to exit
            self.signal_processor_thread.join(timeout=5)
        
        if hasattr(self, 'position_monitor_thread') and self.position_monitor_thread.is_alive():
            self.position_monitor_thread.join(timeout=5)
        
        self.logger.info(f"Trading bot in {self.mode.upper()} mode stopped")
    
    def signal_handler(self, signum, frame):
        """Handle signals for graceful shutdown"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully")
        self.stop()
    
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
            # Default to exchange info
            default_exchange = self.trading_config.get('default_exchange', 'NSE')
            exchange_info = self.data_handler.get_exchange_info(default_exchange)
            return exchange_info.get('is_open', False)
        
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
    
    def _should_process_symbol(self, symbol, timeframe):
        """
        Determine if it's time to process a symbol based on its timeframe
        
        Parameters:
        -----------
        symbol : str
            Symbol to check
        timeframe : str
            Symbol's timeframe
            
        Returns:
        --------
        bool
            True if the symbol should be processed, False otherwise
        """
        # Get current time
        now = datetime.now()
        
        # If we've never processed this symbol, do it now
        if symbol not in self.last_check_time:
            self.last_check_time[symbol] = now
            return True
        
        # Calculate time elapsed since last check
        last_check = self.last_check_time[symbol]
        elapsed = (now - last_check).total_seconds()
        
        # Determine minimum time between checks based on timeframe
        if timeframe == '1m':
            min_seconds = 60
        elif timeframe == '5m':
            min_seconds = 300
        elif timeframe == '15m':
            min_seconds = 900
        elif timeframe == '30m':
            min_seconds = 1800
        elif timeframe == '1h':
            min_seconds = 3600
        elif timeframe == '4h':
            min_seconds = 14400
        elif timeframe == '1d':
            min_seconds = 86400
        else:
            # Default to 1 hour
            min_seconds = 3600
        
        # Check if enough time has elapsed
        if elapsed >= min_seconds:
            self.last_check_time[symbol] = now
            return True
        
        return False
    
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
            prev_candle = self.data_handler.get_previous_candle(symbol, exchange, timeframe)
            if not prev_candle:
                self.logger.warning(f"Could not get previous candle for {symbol}")
                return
            
            # Get current price
            current_price = self.data_handler.get_current_price(symbol, exchange)
            if not current_price:
                self.logger.warning(f"Could not get current price for {symbol}")
                return
            
            # Calculate Gann Square of 9 levels
            gann_results = self.gann_calculator.calculate(prev_candle['close'])
            if not gann_results:
                self.logger.warning(f"Could not calculate Gann levels for {symbol}")
                return
            
            # Check for trading signals
            signal = self._check_for_signal(gann_results, current_price, symbol_type)
            
            if signal:
                self.logger.info(f"Signal generated for {symbol}: {signal['type']}")
                
                # Add signal to queue for processing
                signal_data = {
                    'symbol': symbol,
                    'symbol_info': symbol_info,
                    'signal': signal,
                    'current_price': current_price,
                    'gann_results': gann_results,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.signal_queue.put(signal_data)
            else:
                self.logger.debug(f"No signal generated for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error processing symbol {symbol}: {e}")
    
    def _check_for_signal(self, gann_results, current_price, symbol_type):
        """
        Check for trading signals based on Gann levels and current price
        
        Parameters:
        -----------
        gann_results : dict
            Gann calculation results
        current_price : float
            Current market price
        symbol_type : str
            Symbol type (equity, index, etc.)
            
        Returns:
        --------
        dict or None
            Signal information if a signal is generated, None otherwise
        """
        # Extract key levels
        buy_above = gann_results.get('buy_above')
        sell_below = gann_results.get('sell_below')
        
        # Check for signals based on Gann levels
        if buy_above and current_price > buy_above:
            # Buy signal
            if symbol_type == 'equity':
                # For equity, we can buy the stock and CE option
                return {
                    'type': 'BUY_EQUITY_CE',
                    'level': buy_above,
                    'targets': gann_results.get('buy_targets', []),
                    'stop_loss': gann_results.get('stoploss_long')
                }
            elif symbol_type == 'index':
                # For index, we only buy CE option
                return {
                    'type': 'BUY_CE',
                    'level': buy_above,
                    'targets': gann_results.get('buy_targets', []),
                    'stop_loss': gann_results.get('stoploss_long')
                }
        elif sell_below and current_price < sell_below:
            # Sell signal (for equity we buy PE option, no shorting)
            if symbol_type == 'equity':
                return {
                    'type': 'BUY_PE',
                    'level': sell_below,
                    'targets': gann_results.get('sell_targets', []),
                    'stop_loss': gann_results.get('stoploss_short')
                }
            elif symbol_type == 'index':
                # For index, we buy PE option
                return {
                    'type': 'BUY_PE',
                    'level': sell_below,
                    'targets': gann_results.get('sell_targets', []),
                    'stop_loss': gann_results.get('stoploss_short')
                }
        
        return None
    
    def _process_signals(self):
        """Process trading signals from the queue"""
        self.logger.info("Signal processor thread started")
        
        while self.running:
            try:
                # Get signal from queue with timeout
                signal_data = self.signal_queue.get(timeout=1)
                
                # Check for exit signal
                if signal_data is None:
                    break
                
                # Extract information
                symbol = signal_data['symbol']
                symbol_info = signal_data['symbol_info']
                signal = signal_data['signal']
                current_price = signal_data['current_price']
                
                # Get account information
                account_info = self.api_client.get_funds()
                account_balance = account_info.get('balance', 0)
                
                # Process signal based on type
                if signal['type'] == 'BUY_EQUITY_CE':
                    # Buy equity
                    quantity = self.risk_manager.calculate_position_size(
                        account_balance,
                        current_price,
                        signal['stop_loss']
                    )
                    
                    if quantity <= 0:
                        self.logger.warning(f"Invalid position size calculated for {symbol}: {quantity}")
                        continue
                    
                    # Check if we can place the trade
                    can_trade, reason = self.risk_manager.can_place_trade(
                        symbol,
                        'BUY',
                        quantity,
                        current_price,
                        signal['stop_loss'],
                        signal['targets'][0]['price'] if signal['targets'] else None
                    )
                    
                    if not can_trade:
                        self.logger.warning(f"Cannot place trade for {symbol}: {reason}")
                        continue
                    
                    # Convert symbol if needed
                    symbol_registry = self.symbol_registry
                    algomojo_symbol = symbol_registry.convert_symbol(symbol, 'tv', 'algomojo')
                    
                    # Place equity order
                    equity_result = self.api_client.place_order(
                        symbol=algomojo_symbol,
                        action='BUY',
                        quantity=quantity,
                        price_type='MARKET',
                        exchange=symbol_info.get('exchange')
                    )
                    
                    if equity_result and equity_result.get('status') == 'success':
                        self.logger.info(f"Equity order placed successfully: {equity_result.get('order_id')}")
                        
                        # Register position with risk manager
                        equity_order_id = equity_result.get('order_id')
                        self.risk_manager.register_position(
                            equity_order_id,
                            symbol,
                            'BUY',
                            quantity,
                            current_price,
                            signal['stop_loss'],
                            signal['targets'][0]['price'] if signal['targets'] else None
                        )
                        
                        # Place CE option order
                        lot_size = symbol_info.get('option_lot_size', 1)
                        option_result = self._place_option_order(
                            symbol_info,
                            'CE',
                            current_price,
                            lot_size
                        )
                        
                        if option_result and option_result.get('status') == 'success':
                            self.logger.info(f"CE Option order placed successfully: {option_result.get('order_id')}")
                            
                            # Register option position with risk manager
                            option_order_id = option_result.get('order_id')
                            self.risk_manager.register_position(
                                option_order_id,
                                f"{symbol}-CE",
                                'BUY',
                                lot_size,
                                current_price,
                                signal['stop_loss'],
                                signal['targets'][0]['price'] if signal['targets'] else None
                            )
                        else:
                            self.logger.error(f"Failed to place CE option order: {option_result}")
                    else:
                        self.logger.error(f"Failed to place equity order: {equity_result}")
                
                elif signal['type'] == 'BUY_CE':
                    # For index, only buy CE option
                    lot_size = symbol_info.get('option_lot_size', 1)
                    
                    # Check if we can place the trade
                    can_trade, reason = self.risk_manager.can_place_trade(
                        symbol,
                        'BUY',
                        lot_size,
                        current_price,
                        signal['stop_loss'],
                        signal['targets'][0]['price'] if signal['targets'] else None
                    )
                    
                    if not can_trade:
                        self.logger.warning(f"Cannot place trade for {symbol}: {reason}")
                        continue
                    
                    # Place CE option order
                    option_result = self._place_option_order(
                        symbol_info,
                        'CE',
                        current_price,
                        lot_size
                    )
                    
                    if option_result and option_result.get('status') == 'success':
                        self.logger.info(f"CE Option order placed successfully: {option_result.get('order_id')}")
                        
                        # Register position with risk manager
                        option_order_id = option_result.get('order_id')
                        self.risk_manager.register_position(
                            option_order_id,
                            f"{symbol}-CE",
                            'BUY_CE',
                            lot_size,
                            current_price,
                            signal['stop_loss'],
                            signal['targets'][0]['price'] if signal['targets'] else None
                        )
                    else:
                        self.logger.error(f"Failed to place CE option order: {option_result}")
                
                elif signal['type'] == 'BUY_PE':
                    # Buy PE option
                    lot_size = symbol_info.get('option_lot_size', 1)
                    
                    # Check if we can place the trade
                    can_trade, reason = self.risk_manager.can_place_trade(
                        symbol,
                        'BUY',
                        lot_size,
                        current_price,
                        signal['stop_loss'],
                        signal['targets'][0]['price'] if signal['targets'] else None
                    )
                    
                    if not can_trade:
                        self.logger.warning(f"Cannot place trade for {symbol}: {reason}")
                        continue
                    
                    # Place PE option order
                    option_result = self._place_option_order(
                        symbol_info,
                        'PE',
                        current_price,
                        lot_size
                    )
                    
                    if option_result and option_result.get('status') == 'success':
                        self.logger.info(f"PE Option order placed successfully: {option_result.get('order_id')}")
                        
                        # Register position with risk manager
                        option_order_id = option_result.get('order_id')
                        self.risk_manager.register_position(
                            option_order_id,
                            f"{symbol}-PE",
                            'BUY_PE',
                            lot_size,
                            current_price,
                            signal['stop_loss'],
                            signal['targets'][0]['price'] if signal['targets'] else None
                        )
                    else:
                        self.logger.error(f"Failed to place PE option order: {option_result}")
                
                # Mark signal as processed
                self.signal_queue.task_done()
                
            except queue.Empty:
                # No signals in queue, just continue
                pass
            except Exception as e:
                self.logger.error(f"Error processing signal: {e}")
        
        self.logger.info("Signal processor thread stopped")
    
    def _place_option_order(self, symbol_info, option_type, current_price, quantity):
        """
        Place an option order
        
        Parameters:
        -----------
        symbol_info : dict
            Symbol information
        option_type : str
            "CE" or "PE"
        current_price : float
            Current price of the underlying
        quantity : int
            Order quantity
            
        Returns:
        --------
        dict
            Order result
        """
        symbol = symbol_info.get('symbol')
        symbol_type = symbol_info.get('type', 'equity')
        
        # Get nearest strike price
        strike_price = self._get_nearest_strike(symbol, current_price, option_type == 'PE')
        
        # Get expiry date
        expiry_date = self._get_expiry_date(symbol_type)
        
        # Place option order
        return self.api_client.place_option_order(
            underlying=symbol,
            expiry_date=expiry_date,
            strike_price=strike_price,
            option_type=option_type,
            action='BUY',
            quantity=quantity,
            price_type='MARKET',
            exchange='NFO' if symbol_type in ['equity', 'index'] else 'MCX'
        )
    
    def _get_nearest_strike(self, symbol, price, round_up=False):
        """
        Get nearest strike price for options
        
        Parameters:
        -----------
        symbol : str
            Symbol to get strike for
        price : float
            Current price
        round_up : bool
            Round up instead of down
            
        Returns:
        --------
        float
            Nearest strike price
        """
        # Get strike price intervals from symbol config
        symbol_info = self.active_symbols.get(symbol, {})
        strike_interval = symbol_info.get('strike_interval', 100)  # Default interval
        
        # Calculate nearest strike
        if round_up:
            nearest_strike = math.ceil(price / strike_interval) * strike_interval
        else:
            nearest_strike = math.floor(price / strike_interval) * strike_interval
        
        return nearest_strike
    
    def _get_expiry_date(self, symbol_type):
        """
        Get current expiry date for options
        
        Parameters:
        -----------
        symbol_type : str
            Symbol type (equity, index, etc.)
            
        Returns:
        --------
        str
            Expiry date in format 'DDMMMYYYY'
        """
        # In a real implementation, this would fetch the actual expiry
        # from an API. For this example, we'll use the next Thursday.
        now = datetime.now()
        days_to_thursday = (3 - now.weekday()) % 7
        if days_to_thursday == 0:  # It's Thursday
            if now.hour >= 15:  # After market close
                days_to_thursday = 7
        
        next_thursday = now + timedelta(days=days_to_thursday)
        expiry_date = next_thursday.strftime('%d%b%Y').upper()
        
        return expiry_date
    
    def _monitor_positions_thread(self):
        """Monitor open positions for exit conditions"""
        self.logger.info("Position monitor thread started")
        
        while self.running:
            try:
                # Get open positions from risk manager
                positions = self.risk_manager.get_active_positions()
                
                for order_id, position in positions.items():
                    symbol = position.get('symbol')
                    
                    # Get current price for the symbol
                    if symbol:
                        # Get symbol info
                        symbol_base = symbol.split('-')[0]  # Remove "-CE" or "-PE" suffix
                        symbol_info = self.active_symbols.get(symbol_base)
                        if not symbol_info:
                            continue
                        
                        exchange = symbol_info.get('exchange', 'NSE')
                        current_price = self.data_handler.get_current_price(symbol_base, exchange)
                        
                        if current_price:
                            # Update position with current price
                            position = self.risk_manager.update_position(order_id, current_price)
                            
                            # Check exit conditions
                            should_exit, reason = self.risk_manager.check_exit_conditions(position, current_price)
                            
                            if should_exit:
                                self.logger.info(f"Exit condition met for {symbol}: {reason}")
                                
                                # Close position
                                closed_position = self.risk_manager.close_position(order_id, current_price, reason)
                                
                                if closed_position:
                                    # Execute the exit in the market
                                    symbol_registry = self.symbol_registry
                                    if "-CE" in symbol or "-PE" in symbol:
                                        # It's an option position
                                        algomojo_symbol = symbol_registry.convert_symbol(symbol, 'tv', 'algomojo')
                                        exchange = 'NFO'
                                    else:
                                        # It's an equity position
                                        algomojo_symbol = symbol_registry.convert_symbol(symbol, 'tv', 'algomojo')
                                        exchange = symbol_info.get('exchange', 'NSE')
                                    
                                    exit_result = self.api_client.place_order(
                                        symbol=algomojo_symbol,
                                        action='SELL',
                                        quantity=position.get('quantity', 0),
                                        price_type='MARKET',
                                        exchange=exchange
                                    )
                                   
                                    if exit_result and exit_result.get('status') == 'success':
                                        self.logger.info(f"Successfully closed position for {symbol}: {exit_result.get('order_id')}")
                                    else:
                                        self.logger.error(f"Failed to execute exit for {symbol}: {exit_result}")
                
                # Sleep before checking again
                time.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error monitoring positions: {e}")
                time.sleep(30)  # Sleep longer on errors
        
        self.logger.info("Position monitor thread stopped")
    
    def _close_all_positions(self, reason="Manual"):
        """
        Close all open positions
        
        Parameters:
        -----------
        reason : str
            Reason for closing positions
        """
        self.logger.info(f"Closing all positions, reason: {reason}")
        
        # Use the API client to close all positions 
        result = self.api_client.close_all_positions()
        self.logger.info(f"Close all positions result: {result}")
            
        # Close positions in risk manager
        positions = self.risk_manager.get_active_positions()
            
        for order_id, position in positions.items():
            current_price = position.get('current_price', 0)
            self.risk_manager.close_position(order_id, current_price, reason)
        
    def _save_positions(self):
        """Save positions to file"""
        positions_file = Path("positions.json")
        
        try:
            # Get positions from risk manager
            positions = self.risk_manager.get_active_positions()
            
            # Save to file
            with open(positions_file, 'w') as f:
                json.dump(positions, f, indent=4)
            
            self.logger.info(f"Saved {len(positions)} positions to {positions_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving positions: {e}")
    
    def main():
        """Main entry point for the trading bot"""
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Gann Square of 9 Trading Bot')
        parser.add_argument('--mode', '-m', choices=['paper', 'live'], default='paper',
                        help='Trading mode (paper or live)')
        parser.add_argument('--config', '-c', default='config',
                        help='Path to configuration directory')
        parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug logging')
        
        args = parser.parse_args()
        
        # Create and start the trading bot
        trading_bot = GannTradingBot(
            config_path=args.config,
            mode=args.mode,
            debug=args.debug
        )
        
        trading_bot.start()
    
    if __name__ == "__main__":
        main()