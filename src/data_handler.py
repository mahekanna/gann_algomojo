# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 21:32:53 2025

@author: mahes
"""

# src/data_handler.py

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import math

class DataHandler:
    """
    Handles market data retrieval and processing
    """
    
    def __init__(self, api_config):
        """
        Initialize the data handler with API configuration
        
        Parameters:
        -----------
        api_config : dict
            Dictionary containing API credentials
            - api_key: AlgoMojo API key
            - api_secret: AlgoMojo API secret
            - broker_code: Broker code
        """
        self.logger = logging.getLogger(__name__)
        
        # API configuration
        self.api_key = api_config.get('api_key')
        self.api_secret = api_config.get('api_secret')
        self.broker_code = api_config.get('broker_code')
        
        # Initialize cache for data
        self.data_cache = {}
        self.cache_expiry = {}
        self.cache_duration = 300  # Cache duration in seconds (5 minutes)
        
        # Connect to API if needed
        try:
            from algomojo.pyapi import api
            self.algomojo = api(api_key=self.api_key, api_secret=self.api_secret)
            self.logger.info("AlgoMojo API connection established for data handler")
        except Exception as e:
            self.logger.error(f"Failed to initialize AlgoMojo API for data: {e}")
            self.algomojo = None
    
    def get_historical_data(self, symbol, timeframe='1D', limit=50):
        """
        Get historical price data for a symbol
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        timeframe : str
            Time interval ('1m', '5m', '15m', '30m', '1H', '1D', etc.)
        limit : int
            Number of candles to retrieve
            
        Returns:
        --------
        pandas.DataFrame
            DataFrame with historical price data
        """
        cache_key = f"{symbol}_{timeframe}_{limit}"
        
        # Check if we have cached data that's still valid
        if cache_key in self.data_cache and cache_key in self.cache_expiry:
            if datetime.now().timestamp() < self.cache_expiry[cache_key]:
                self.logger.debug(f"Using cached data for {cache_key}")
                return self.data_cache[cache_key]
        
        try:
            # In a real implementation, you would fetch data from the broker API
            # Here we'll implement a placeholder that creates simulated data
            # since AlgoMojo doesn't provide historical data in the example code
            
            self.logger.info(f"Fetching historical data for {symbol} on {timeframe} timeframe")
            
            # Check if we have API access
            if self.algomojo:
                # Try to get the current quote first to see if the symbol is valid
                quote = self.algomojo.GetQuote(
                    broker=self.broker_code,
                    exchange="NSE",  # Assumed exchange, adjust as needed
                    symbol=symbol
                )
                
                if not quote or "data" not in quote:
                    self.logger.warning(f"Could not get quote for {symbol}, using simulated data")
                    last_price = 1000.0  # Simulated price
                else:
                    last_price = float(quote["data"].get("last_price", 1000.0))
                
                # Generate simulated historical data since API example doesn't show
                # how to get historical data
                data = self._generate_simulated_data(symbol, timeframe, limit, last_price)
            else:
                # No API access, generate completely simulated data
                self.logger.warning("No API access, using fully simulated data")
                data = self._generate_simulated_data(symbol, timeframe, limit)
            
            # Cache the data
            self.data_cache[cache_key] = data
            self.cache_expiry[cache_key] = datetime.now().timestamp() + self.cache_duration
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    def _generate_simulated_data(self, symbol, timeframe, limit, last_price=None):
        """
        Generate simulated historical data for testing
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        timeframe : str
            Time interval
        limit : int
            Number of candles
        last_price : float
            Current price to use as reference (if available)
            
        Returns:
        --------
        pandas.DataFrame
            DataFrame with simulated price data
        """
        # Set end time to now
        end_time = datetime.now()
        
        # Determine time delta based on timeframe
        if timeframe == '1m':
            delta = timedelta(minutes=1)
        elif timeframe == '5m':
            delta = timedelta(minutes=5)
        elif timeframe == '15m':
            delta = timedelta(minutes=15)
        elif timeframe == '30m':
            delta = timedelta(minutes=30)
        elif timeframe == '1H':
            delta = timedelta(hours=1)
        elif timeframe == '1D':
            delta = timedelta(days=1)
        else:
            # Default to daily
            delta = timedelta(days=1)
        
        # Generate timestamps
        timestamps = [end_time - i * delta for i in range(limit)]
        timestamps.reverse()  # Oldest first
        
        # Use provided last price or generate a random one
        if last_price is None:
            last_price = np.random.uniform(100, 10000)
        
        # Generate price data with some randomness but trending
        trend = np.random.choice([-1, 1]) * 0.1  # Random trend direction
        
        # Start with the "oldest" price
        start_price = last_price * (1 - trend * limit * 0.01)
        
        # Generate price series with random walk and trend
        prices = [start_price]
        for i in range(1, limit):
            # Add some random variation and the trend
            next_price = prices[-1] * (1 + np.random.normal(trend, 0.01))
            prices.append(next_price)
        
        # Create OHLC data
        data = []
        for i, timestamp in enumerate(timestamps):
            base_price = prices[i]
            high_price = base_price * (1 + abs(np.random.normal(0, 0.005)))
            low_price = base_price * (1 - abs(np.random.normal(0, 0.005)))
            
            # Ensure the last candle ends at last_price if provided
            if i == len(timestamps) - 1 and last_price is not None:
                close_price = last_price
            else:
                # Random close price between high and low
                close_price = np.random.uniform(low_price, high_price)
            
            # Determine open price
            if i == 0:
                open_price = base_price
            else:
                # Open at previous close
                open_price = data[-1]['close']
            
            # Ensure high >= open, close and low <= open, close
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            # Generate random volume
            volume = int(np.random.uniform(1000, 10000))
            
            data.append({
                'timestamp': timestamp,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def get_current_price(self, symbol, exchange="NSE"):
        """
        Get current market price for a symbol
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange identifier
            
        Returns:
        --------
        float
            Current market price
        """
        try:
            if self.algomojo:
                quote = self.algomojo.GetQuote(
                    broker=self.broker_code,
                    exchange=exchange,
                    symbol=symbol
                )
                
                if quote and "data" in quote:
                    last_price = quote["data"].get("last_price")
                    if last_price:
                        return float(last_price)
            
            # Fallback to using cached data if available
            cache_key = f"{symbol}_1m_10"
            if cache_key in self.data_cache:
                df = self.data_cache[cache_key]
                if not df.empty:
                    return df.iloc[-1]['close']
            
            # If all else fails, generate a simulated price
            self.logger.warning(f"Could not get current price for {symbol}, using simulated price")
            return np.random.uniform(100, 10000)
            
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def get_option_chain(self, underlying, expiry_date=None):
        """
        Get option chain data for an underlying
        
        Parameters:
        -----------
        underlying : str
            Underlying symbol (e.g. "NIFTY", "BANKNIFTY")
        expiry_date : str
            Optional expiry date (format as required by broker)
            If None, uses the nearest expiry date
            
        Returns:
        --------
        pandas.DataFrame
            DataFrame with option chain data
        """
        try:
            self.logger.info(f"Fetching option chain for {underlying}")
            
            # In a real implementation, you would fetch from the broker API
            # Here we'll simulate option chain data since AlgoMojo example 
            # doesn't show how to get option chain
            
            # Get current price of underlying
            underlying_price = self.get_current_price(underlying)
            if not underlying_price:
                self.logger.error(f"Could not get underlying price for {underlying}")
                return None
            
            # Round to nearest strike interval
            atm_strike = self._get_nearest_strike(underlying_price, underlying)
            
            # Generate strikes around ATM
            strikes = []
            num_strikes = 10  # Generate 10 strikes above and below ATM
            strike_interval = self._get_strike_interval(underlying)
            
            for i in range(-num_strikes, num_strikes + 1):
                strikes.append(atm_strike + i * strike_interval)
            
            # If no expiry provided, generate the nearest expiry
            if not expiry_date:
                expiry_date = self._get_nearest_expiry()
            
            # Generate option data for each strike
            option_data = []
            
            for strike in strikes:
                # Calculate theoretical prices
                ce_price = self._calculate_option_price(underlying_price, strike, 0.2, 30, 'CE')
                pe_price = self._calculate_option_price(underlying_price, strike, 0.2, 30, 'PE')
                
                ce_symbol = f"{underlying}{expiry_date}{strike}CE"
                pe_symbol = f"{underlying}{expiry_date}{strike}PE"
                
                # CE option
                option_data.append({
                    'symbol': ce_symbol,
                    'underlying': underlying,
                    'expiry': expiry_date,
                    'strike': strike,
                    'option_type': 'CE',
                    'last_price': ce_price,
                    'bid': ce_price * 0.98,
                    'ask': ce_price * 1.02,
                    'volume': int(np.random.uniform(100, 10000)),
                    'oi': int(np.random.uniform(1000, 100000))
                })
                
                # PE option
                option_data.append({
                    'symbol': pe_symbol,
                    'underlying': underlying,
                    'expiry': expiry_date,
                    'strike': strike,
                    'option_type': 'PE',
                    'last_price': pe_price,
                    'bid': pe_price * 0.98,
                    'ask': pe_price * 1.02,
                    'volume': int(np.random.uniform(100, 10000)),
                    'oi': int(np.random.uniform(1000, 100000))
                })
            
            # Convert to DataFrame
            df = pd.DataFrame(option_data)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching option chain for {underlying}: {e}")
            return None
    
    def _get_nearest_strike(self, price, underlying):
        """
        Get the nearest strike price for an underlying
        
        Parameters:
        -----------
        price : float
            Current price
        underlying : str
            Underlying symbol
            
        Returns:
        --------
        float
            Nearest strike price
        """
        # Get strike interval based on underlying
        interval = self._get_strike_interval(underlying)
        
        # Round to nearest interval
        return round(price / interval) * interval
    
    def _get_strike_interval(self, underlying):
        """
        Get the strike interval for an underlying
        
        Parameters:
        -----------
        underlying : str
            Underlying symbol
            
        Returns:
        --------
        float
            Strike interval
        """
        # Define strike intervals for common underlyings
        intervals = {
            'NIFTY': 50.0,
            'BANKNIFTY': 100.0,
            'FINNIFTY': 50.0,
            # Add more as needed
        }
        
        # Return the interval for the underlying or a default value
        return intervals.get(underlying, 10.0)
    
    def _get_nearest_expiry(self):
        """
        Get the nearest expiry date
        
        Returns:
        --------
        str
            Nearest expiry date string (format depends on broker requirements)
        """
        today = datetime.now()
        
        # Calculate this week's Thursday (common weekly expiry for index options)
        days_to_thursday = (3 - today.weekday()) % 7
        thursday = today + timedelta(days=days_to_thursday)
        
        # If it's past Thursday, get next week's Thursday
        if days_to_thursday == 0 and today.hour >= 15:  # After 3 PM on Thursday
            thursday = today + timedelta(days=7)
        
        # Format the date (format depends on broker requirements)
        # Example: "23JUN" or "23JUN23" or "29JUN2023"
        month_str = thursday.strftime("%b").upper()
        return f"{thursday.day:02d}{month_str}"
    
    def _calculate_option_price(self, underlying_price, strike, volatility, days_to_expiry, option_type):
        """
        Calculate a simple theoretical option price
        
        Parameters:
        -----------
        underlying_price : float
            Current price of the underlying
        strike : float
            Strike price
        volatility : float
            Implied volatility (decimal)
        days_to_expiry : int
            Days to expiry
        option_type : str
            'CE' or 'PE'
            
        Returns:
        --------
        float
            Theoretical option price
        """
        # This is a very simplified model - in reality you'd use Black-Scholes
        # or a similar model to calculate option prices
        
        if option_type == 'CE':
            # Call option - simplified calculation
            intrinsic = max(0, underlying_price - strike)
            time_value = underlying_price * volatility * math.sqrt(days_to_expiry / 365)
            return round(intrinsic + time_value, 2)
        else:
            # Put option - simplified calculation
            intrinsic = max(0, strike - underlying_price)
            time_value = underlying_price * volatility * math.sqrt(days_to_expiry / 365)
            return round(intrinsic + time_value, 2)
    
    def get_market_status(self):
        """
        Check if the market is currently open
        
        Returns:
        --------
        bool
            True if market is open, False otherwise
        """
        try:
            # In a real implementation, you would fetch from broker API
            # Here we'll use a simple time-based check
            
            now = datetime.now()
            
            # Check if it's a weekday (0 = Monday, 4 = Friday)
            if now.weekday() > 4:
                return False
            
            # Check if within market hours (9:15 AM to 3:30 PM IST)
            market_open = now.replace(hour=9, minute=15, second=0)
            market_close = now.replace(hour=15, minute=30, second=0)
            
            return market_open <= now <= market_close
            
        except Exception as e:
            self.logger.error(f"Error checking market status: {e}")
            return False
    
    def clear_cache(self, symbol=None, timeframe=None):
        """
        Clear data cache
        
        Parameters:
        -----------
        symbol : str
            Optional symbol to clear cache for
        timeframe : str
            Optional timeframe to clear cache for
        """
        if symbol and timeframe:
            # Clear specific cache
            key = f"{symbol}_{timeframe}_"
            to_remove = [k for k in self.data_cache.keys() if k.startswith(key)]
            for k in to_remove:
                if k in self.data_cache:
                    del self.data_cache[k]
                if k in self.cache_expiry:
                    del self.cache_expiry[k]
        elif symbol:
            # Clear all timeframes for a symbol
            to_remove = [k for k in self.data_cache.keys() if k.startswith(f"{symbol}_")]
            for k in to_remove:
                if k in self.data_cache:
                    del self.data_cache[k]
                if k in self.cache_expiry:
                    del self.cache_expiry[k]
        else:
            # Clear all cache
            self.data_cache = {}
            self.cache_expiry = {}
        
        self.logger.info(f"Cache cleared: symbol={symbol}, timeframe={timeframe}")
    
    def get_exchange_trading_hours(self, exchange="NSE"):
        """
        Get trading hours for an exchange
        
        Parameters:
        -----------
        exchange : str
            Exchange identifier
            
        Returns:
        --------
        dict
            Dictionary with trading hours information
        """
        # Trading hours for common exchanges
        exchange_hours = {
            "NSE": {
                "open": "09:15",
                "close": "15:30",
                "timezone": "Asia/Kolkata"
            },
            "BSE": {
                "open": "09:15",
                "close": "15:30",
                "timezone": "Asia/Kolkata"
            },
            "NFO": {
                "open": "09:15",
                "close": "15:30",
                "timezone": "Asia/Kolkata"
            }
        }
        
        return exchange_hours.get(exchange, {
            "open": "09:15",
            "close": "15:30",
            "timezone": "Asia/Kolkata"
        })

    def save_historical_data(self, symbol, timeframe, data, filename=None):
        """
        Save historical data to a CSV file
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        timeframe : str
            Time interval
        data : pandas.DataFrame
            DataFrame with historical data
        filename : str
            Optional filename, if None generates based on symbol and timeframe
            
        Returns:
        --------
        str
            Path to saved file
        """
        if filename is None:
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"data_{symbol}_{timeframe}_{date_str}.csv"
        
        try:
            data.to_csv(filename)
            self.logger.info(f"Historical data saved to {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Error saving historical data: {e}")
            return None
    
    def load_historical_data(self, filename):
        """
        Load historical data from a CSV file
        
        Parameters:
        -----------
        filename : str
            Path to CSV file
            
        Returns:
        --------
        pandas.DataFrame
            DataFrame with historical data
        """
        try:
            df = pd.read_csv(filename, index_col=0, parse_dates=True)
            self.logger.info(f"Historical data loaded from {filename}")
            return df
        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}")
            return None