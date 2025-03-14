# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 23:10:00 2025

@author: mahes
"""

# gann_trading_system.py

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
from src.gann_calculator import GannCalculator
from src.risk_manager import RiskManager
from src.logger import setup_logger, TradeLogger

# Import trading executors
from src.paper_trade_executor import PaperTradeExecutor
from src.live_trade_executor import LiveTradeExecutor

class GannTradingSystem:
    """
    Gann Square of 9 Trading System with support for both paper and live trading
    """
    
    def __init__(self, config_path="config", mode="paper"):
        """
        Initialize the trading system
        
        Parameters:
        -----------
        config_path : str
            Path to configuration files
        mode : str
            Trading mode ("paper" or "live")
        """
        # Setup logging
        self.logger = setup_logger()
        self.trade_logger = TradeLogger()
        
        # Set trading mode
        self.mode = mode.lower()
        if self.mode not in ["paper", "live"]:
            self.logger.warning(f"Invalid mode: {mode}, defaulting to paper trading")
            self.mode = "paper"
        
        self.logger.info(f"Initializing Gann Trading System in {self.mode.upper()} mode")
        
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
            # Initialize data handler
            self.data_handler = TVDataHandler()
            
            # Initialize Gann calculator
            gann_params = self.trading_config.get('gann_parameters', {})
            self.gann_calculator = GannCalculator(gann_params)
            
            # Initialize trade executor based on mode
            if self.mode == "paper":
                self.trade_executor = PaperTradeExecutor(
                    self.api_config, 
                    self.trading_config
                )
                self.logger.info("Using PaperTradeExecutor for paper trading")
            else:
                self.trade_executor = LiveTradeExecutor(
                    self.api_config, 
                    self.trading_config
                )
                self.logger.info("Using LiveTradeExecutor for live trading")
            
            # Initialize risk manager
            risk_params = self.trading_config.get('risk_parameters', {})
            self.risk_manager = RiskManager(risk_params)
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise
    
    def start(self):
        """Start the trading system"""
        if self.running:
            self.logger.warning("System is already running")
            return
        
        self.running = True
        self.logger.info(f"Starting Gann Square of 9 Trading System in {self.mode.upper()} mode")
        
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
            self.logger.info("System stopped by user")
        except Exception as e:
            self.logger.error(f"Error in main trading loop: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the trading system"""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping trading system")
        
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
        
        self.logger.info(f"Trading system in {self.mode.upper()} mode stopped")
    
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
            prev_candle = self.data_handler.