# -*- coding: utf-8 -*-
"""
Created on Fri Mar 14 00:29:24 2025

@author: mahes
"""

# src/tvdata_handler.py

import logging
import pandas as pd
from datetime import datetime, timedelta
import time
from pathlib import Path
from src.symbol_registry import SymbolRegistry

class TVDataHandler:
    """
    Data handler that uses tvDatafeed to get TradingView data
    """
    
    def __init__(self, config_dir="config"):
        """
        Initialize the TV data handler
        
        Parameters:
        -----------
        config_dir : str
            Directory containing configuration files
        """
        self.logger = logging.getLogger(__name__)
        self.config_dir = Path(config_dir)
        self.symbol_registry = SymbolRegistry(config_dir)
        
        try:
            # Import tvDatafeed
            from tvDatafeed import TvDatafeed, Interval
            
            # Store interval mappings
            self.intervals = {
                "1m": Interval.in_1_minute,
                "3m": Interval.in_3_minute,
                "5m": Interval.in_5_minute,
                "15m": Interval.in_15_minute,
                "30m": Interval.in_30_minute,
                "45m": Interval.in_45_minute,
                "1h": Interval.in_1_hour,
                "2h": Interval.in_2_hour,
                "3h": Interval.in_3_hour,
                "4h": Interval.in_4_hour,
                "1d": Interval.in_daily,
                "1w": Interval.in_weekly,
                "1M": Interval.in_monthly
            }
            
            # Initialize TvDatafeed (no login required for basic data)
            self.tv = TvDatafeed()
            self.logger.info("TvDatafeed initialized successfully")
            
        except ImportError:
            self.logger.error("tvDatafeed not installed. Install with: pip install tvDatafeed")
            raise
    
    def get_previous_candle(self, symbol, exchange="NSE", timeframe="1h", adjust_symbol=True):
        """
        Get the previous completed candle for a symbol
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange (default: NSE)
        timeframe : str
            Timeframe (1m, 5m, 15m, 1h, 1d, etc.)
        adjust_symbol : bool
            Whether to adjust symbol format for TradingView
            
        Returns:
        --------
        dict
            Previous candle data with OHLCV values
        """
        try:
            # Convert from AlgoMojo format to TradingView format if needed
            if adjust_symbol:
                tv_symbol = self.symbol_registry.map_symbol(symbol, "algomojo", "tv")
            else:
                tv_symbol = symbol
            
            # Log the conversion
            if tv_symbol != symbol:
                self.logger.debug(f"Converted symbol for TradingView: {symbol} -> {tv_symbol}")
            
            # Convert timeframe to lowercase for consistency
            timeframe = timeframe.lower()
            
            # Map to tvDatafeed interval
            if timeframe in self.intervals:
                interval = self.intervals[timeframe]
            else:
                self.logger.warning(f"Unknown timeframe: {timeframe}, defaulting to 1h")
                interval = self.intervals["1h"]
            
            # Handle special exchange mappings for commodities
            if exchange == "MCX":
                # For MCX symbols, use MCX prefix in TradingView
                if not tv_symbol.startswith("MCX:") and not tv_symbol.endswith("1!"):
                    tv_symbol = f"MCX:{tv_symbol}"
            
            # Get data from TradingView - fetch a few candles to ensure we have the previous one
            data = self.tv.get_hist(
                symbol=tv_symbol,
                exchange=exchange,
                interval=interval,
                n_bars=5  # Get 5 bars to ensure we have the previous completed candle
            )
            
            if data is None or len(data) < 2:
                self.logger.error(f"Could not retrieve data for {tv_symbol}:{exchange} on {timeframe}")
                return None
            
            # Get the previous candle (second to last in the dataframe)
            prev_candle = data.iloc[-2]
            
            # Convert to dictionary
            candle_dict = {
                'open': float(prev_candle['open']),
                'high': float(prev_candle['high']),
                'low': float(prev_candle['low']),
                'close': float(prev_candle['close']),
                'volume': float(prev_candle['volume']),
                'timestamp': prev_candle.name.to_pydatetime()  # Convert index to datetime
            }
            
            self.logger.info(f"Retrieved previous candle for {tv_symbol}:{exchange} on {timeframe}")
            return candle_dict
            
        except Exception as e:
            self.logger.error(f"Error getting previous candle for {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol, exchange="NSE", adjust_symbol=True):
        """
        Get the current market price for a symbol
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange (default: NSE)
        adjust_symbol : bool
            Whether to adjust symbol format for TradingView
            
        Returns:
        --------
        float
            Current market price
        """
        try:
            # Convert from AlgoMojo format to TradingView format if needed
            if adjust_symbol:
                tv_symbol = self.symbol_registry.map_symbol(symbol, "algomojo", "tv")
            else:
                tv_symbol = symbol
            
            # Log the conversion
            if tv_symbol != symbol:
                self.logger.debug(f"Converted symbol for TradingView: {symbol} -> {tv_symbol}")
            
            # Handle special exchange mappings for commodities
            if exchange == "MCX":
                # For MCX symbols, use MCX prefix in TradingView
                if not tv_symbol.startswith("MCX:") and not tv_symbol.endswith("1!"):
                    tv_symbol = f"MCX:{tv_symbol}"
            
            # Get the most recent 1-minute candle
            data = self.tv.get_hist(
                symbol=tv_symbol,
                exchange=exchange,
                interval=self.intervals["1m"],
                n_bars=1
            )
            
            if data is None or len(data) < 1:
                self.logger.error(f"Could not retrieve current price for {tv_symbol}:{exchange}")
                return None
            
            # Get the closing price of the most recent candle
            current_price = float(data.iloc[-1]['close'])
            
            return current_price
            
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol, timeframe="1d", limit=50, exchange="NSE", adjust_symbol=True):
        """
        Get historical price data for a symbol
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        timeframe : str
            Time interval (1m, 5m, 15m, 1h, 1d, etc.)
        limit : int
            Number of candles to retrieve
        exchange : str
            Exchange (default: NSE)
        adjust_symbol : bool
            Whether to adjust symbol format for TradingView
            
        Returns:
        --------
        pandas.DataFrame
            DataFrame with historical price data
        """
        try:
            # Convert from AlgoMojo format to TradingView format if needed
            if adjust_symbol:
                tv_symbol = self.symbol_registry.map_symbol(symbol, "algomojo", "tv")
            else:
                tv_symbol = symbol
            
            # Convert timeframe to lowercase for consistency
            timeframe = timeframe.lower()
            
            # Map to tvDatafeed interval
            if timeframe in self.intervals:
                interval = self.intervals[timeframe]
            else:
                self.logger.warning(f"Unknown timeframe: {timeframe}, defaulting to 1d")
                interval = self.intervals["1d"]
            
            # Handle special exchange mappings for commodities
            if exchange == "MCX":
                # For MCX symbols, use MCX prefix in TradingView
                if not tv_symbol.startswith("MCX:") and not tv_symbol.endswith("1!"):
                    tv_symbol = f"MCX:{tv_symbol}"
            
            # Get data from TradingView
            data = self.tv.get_hist(
                symbol=tv_symbol,
                exchange=exchange,
                interval=interval,
                n_bars=limit
            )
            
            if data is None:
                self.logger.error(f"Could not retrieve historical data for {tv_symbol}:{exchange} on {timeframe}")
                return None
            
            self.logger.info(f"Retrieved historical data for {tv_symbol}:{exchange} on {timeframe} ({len(data)} candles)")
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
            
    def get_exchange_info(self, exchange="NSE"):
        """
        Get exchange information
        
        Parameters:
        -----------
        exchange : str
            Exchange identifier
            
        Returns:
        --------
        dict
            Exchange information
        """
        # Trading hours for common Indian exchanges
        exchange_hours = {
            "NSE": {
                "open": "09:15",
                "close": "15:30",
                "timezone": "Asia/Kolkata",
                "is_open": self._is_exchange_open("NSE")
            },
            "BSE": {
                "open": "09:15",
                "close": "15:30",
                "timezone": "Asia/Kolkata",
                "is_open": self._is_exchange_open("BSE")
            },
            "NFO": {
                "open": "09:15",
                "close": "15:30",
                "timezone": "Asia/Kolkata",
                "is_open": self._is_exchange_open("NFO")
            },
            "MCX": {
                "open": "09:00",
                "close": "23:30",
                "timezone": "Asia/Kolkata",
                "is_open": self._is_exchange_open("MCX")
            }
        }
        
        return exchange_hours.get(exchange, {
            "open": "09:15",
            "close": "15:30",
            "timezone": "Asia/Kolkata",
            "is_open": False
        })
    
    def _is_exchange_open(self, exchange):
        """
        Check if an exchange is currently open
        
        Parameters:
        -----------
        exchange : str
            Exchange identifier
            
        Returns:
        --------
        bool
            True if exchange is open, False otherwise
        """
        # Get current time in India
        try:
            import pytz
            india_tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(india_tz)
        except ImportError:
            # Fallback if pytz is not available
            now = datetime.now()
        
        # Check if it's a weekday (0=Monday, 4=Friday)
        if now.weekday() > 4:
            return False
        
        # Get exchange hours
        if exchange == "MCX":
            # MCX has different trading hours
            market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
            market_close = now.replace(hour=23, minute=30, second=0, microsecond=0)
        else:
            # Standard NSE/BSE hours
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return market_open <= now <= market_close