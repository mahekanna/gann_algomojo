# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 23:29:18 2025

@author: mahes
"""

# -*- coding: utf-8 -*-
"""
TradingView Data Handler

This module provides functionality to fetch market data from TradingView
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
import json
import os
from pathlib import Path
from tvDatafeed import TvDatafeed

class TVDataHandler:
    """
    Handles data retrieval from TradingView
    """
    
    def __init__(self, config_path: Union[str, Path], username: str = '', password: str = ''):
        """
        Initialize the TradingView data handler
        
        Parameters:
        -----------
        config_path : str or Path
            Path to configuration directory
        username : str, optional
            TradingView username
        password : str, optional
            TradingView password
        """
        self.logger = logging.getLogger(__name__)
        
        # Convert config_path to Path object if it's a string
        if isinstance(config_path, str):
            config_path = Path(config_path)
        
        self.config_path = config_path
        
        # Load symbol mapping configuration
        self.symbol_registry = self._load_symbol_registry()
        
        # Initialize tvDatafeed client
        try:
            self.tv = TvDatafeed(username, password)
            self.logger.info("TradingView data feed initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize TradingView data feed: {e}")
            self.tv = None
    
    def _load_symbol_registry(self) -> Dict[str, Any]:
        """
        Load symbol registry from configuration
        
        Returns:
        --------
        dict
            Symbol registry data
        """
        try:
            symbols_file = self.config_path / "symbols.json"
            
            if not symbols_file.exists():
                self.logger.error("Symbols configuration file not found")
                return {}
            
            with open(symbols_file, 'r') as f:
                symbols_config = json.load(f)
            
            registry = {}
            
            for symbol_info in symbols_config.get('symbols', []):
                symbol = symbol_info.get('symbol')
                if symbol:
                    registry[symbol] = symbol_info
            
            self.logger.info(f"Loaded {len(registry)} symbols")
            return registry
            
        except Exception as e:
            self.logger.error(f"Error loading symbol registry: {e}")
            return {}
    
    def get_current_price(self, symbol: str, exchange: str = 'NSE') -> Optional[float]:
        """
        Get current price for a symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol to get price for
        exchange : str
            Exchange (NSE, BSE, MCX)
            
        Returns:
        --------
        float or None
            Current price or None if not available
        """
        # Get the TradingView symbol from registry
        symbol_info = self.symbol_registry.get(symbol, {})
        tv_symbol = symbol_info.get('tv_symbol', symbol)
        
        try:
            # Get the last candle (current price)
            data = self.tv.get_hist(
                symbol=tv_symbol,
                exchange=exchange,
                interval='1m',
                n_bars=1
            )
            
            if data is not None and not data.empty:
                return float(data['close'].iloc[-1])
            else:
                self.logger.warning(f"No data returned for {symbol} on {exchange}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def get_previous_candle(self, 
                          symbol: str, 
                          exchange: str = 'NSE', 
                          timeframe: str = '1h') -> Optional[Dict[str, Any]]:
        """
        Get previous completed candle for a symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol to get candle for
        exchange : str
            Exchange (NSE, BSE, MCX)
        timeframe : str
            Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            
        Returns:
        --------
        dict or None
            Previous candle data or None if not available
        """
        # Get the TradingView symbol from registry
        symbol_info = self.symbol_registry.get(symbol, {})
        tv_symbol = symbol_info.get('tv_symbol', symbol)
        
        try:
            # Normalize timeframe format
            interval = timeframe.lower()
            
            # Get the last 2 candles (previous and current)
            data = self.tv.get_hist(
                symbol=tv_symbol,
                exchange=exchange,
                interval=interval,
                n_bars=2
            )
            
            if data is not None and not data.empty and len(data) >= 2:
                # Get the previous (completed) candle
                candle = data.iloc[-2]
                
                return {
                    'symbol': symbol,
                    'exchange': exchange,
                    'timeframe': timeframe,
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': float(candle['volume']) if 'volume' in candle else 0,
                    'timestamp': candle.name.isoformat() if hasattr(candle.name, 'isoformat') else str(candle.name)
                }
            else:
                self.logger.warning(f"No previous candle data for {symbol} on {exchange} ({timeframe})")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting previous candle for {symbol}: {e}")
            return None
    
    def get_historical_data(self, 
                          symbol: str, 
                          exchange: str = 'NSE', 
                          timeframe: str = '1h',
                          n_bars: int = 100) -> Optional[pd.DataFrame]:
        """
        Get historical data for a symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol to get data for
        exchange : str
            Exchange (NSE, BSE, MCX)
        timeframe : str
            Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)
        n_bars : int
            Number of bars to retrieve
            
        Returns:
        --------
        pandas.DataFrame or None
            Historical data or None if not available
        """
        # Get the TradingView symbol from registry
        symbol_info = self.symbol_registry.get(symbol, {})
        tv_symbol = symbol_info.get('tv_symbol', symbol)
        
        try:
            # Normalize timeframe format
            interval = timeframe.lower()
            
            # Get historical data
            data = self.tv.get_hist(
                symbol=tv_symbol,
                exchange=exchange,
                interval=interval,
                n_bars=n_bars
            )
            
            return data
                
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    def get_exchange_info(self, exchange: str = 'NSE') -> Dict[str, Any]:
        """
        Get exchange information including trading hours and status
        
        Parameters:
        -----------
        exchange : str
            Exchange code (NSE, BSE, MCX)
            
        Returns:
        --------
        dict
            Exchange information
        """
        # Hard-coded exchange info for now
        # In a production environment, this could be fetched from an API
        exchange_info = {
            'NSE': {
                'name': 'National Stock Exchange of India',
                'country': 'India',
                'timezone': 'Asia/Kolkata',
                'trading_hours': {
                    'start': '09:15',
                    'end': '15:30'
                },
                'weekly_holidays': [5, 6],  # Saturday and Sunday
                'is_open': self._is_exchange_open('NSE')
            },
            'BSE': {
                'name': 'Bombay Stock Exchange',
                'country': 'India',
                'timezone': 'Asia/Kolkata',
                'trading_hours': {
                    'start': '09:15',
                    'end': '15:30'
                },
                'weekly_holidays': [5, 6],  # Saturday and Sunday
                'is_open': self._is_exchange_open('BSE')
            },
            'MCX': {
                'name': 'Multi Commodity Exchange of India',
                'country': 'India',
                'timezone': 'Asia/Kolkata',
                'trading_hours': {
                    'start': '09:00',
                    'end': '23:30'
                },
                'weekly_holidays': [5, 6],  # Saturday and Sunday
                'is_open': self._is_exchange_open('MCX')
            }
        }
        
        return exchange_info.get(exchange.upper(), {})
    
    def _is_exchange_open(self, exchange: str) -> bool:
        """
        Check if an exchange is currently open for trading
        
        Parameters:
        -----------
        exchange : str
            Exchange code (NSE, BSE, MCX)
            
        Returns:
        --------
        bool
            True if exchange is open, False otherwise
        """
        now = datetime.now()
        
        # Check if it's a weekday (0=Monday, 4=Friday)
        if now.weekday() > 4:  # Saturday or Sunday
            return False
        
        # Define trading hours based on exchange
        if exchange.upper() in ['NSE', 'BSE']:
            start_time = datetime.strptime('09:15', '%H:%M').time()
            end_time = datetime.strptime('15:30', '%H:%M').time()
        elif exchange.upper() == 'MCX':
            start_time = datetime.strptime('09:00', '%H:%M').time()
            end_time = datetime.strptime('23:30', '%H:%M').time()
        else:
            return False
        
        # Check if current time is within trading hours
        return start_time <= now.time() <= end_time