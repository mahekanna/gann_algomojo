# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 23:06:53 2025

@author: mahes
"""

# src/option_helpers.py

import math
from datetime import datetime, timedelta

class OptionHelpers:
    """
    Helper functions for options trading with Gann Square of 9
    """
    
    @staticmethod
    def get_atm_strike(current_price, symbol=None, strike_interval=None, round_up=False):
        """
        Get the at-the-money strike price
        
        Parameters:
        -----------
        current_price : float
            Current price of the underlying
        symbol : str
            Symbol name for predefined intervals
        strike_interval : float
            Strike price interval (if known)
        round_up : bool
            Whether to round up (True) or down (False)
            
        Returns:
        --------
        float
            At-the-money strike price
        """
        # Determine strike interval if not provided
        if strike_interval is None:
            if symbol in ['NIFTY', 'NIFTY50']:
                strike_interval = 50
            elif symbol in ['BANKNIFTY', 'NIFTYBANK']:
                strike_interval = 100
            elif symbol in ['FINNIFTY']:
                strike_interval = 50
            else:
                # For stocks, use percentage of price
                price_percent = current_price * 0.01
                
                if price_percent < 5:
                    strike_interval = 5
                elif price_percent < 10:
                    strike_interval = 10
                elif price_percent < 25:
                    strike_interval = 25
                elif price_percent < 50:
                    strike_interval = 50
                else:
                    strike_interval = 100
        
        # Calculate nearest strike
        if round_up:
            return math.ceil(current_price / strike_interval) * strike_interval
        else:
            return math.floor(current_price / strike_interval) * strike_interval
    
    @staticmethod
    def get_option_strike_type(current_price, strike_price, option_type):
        """
        Determine if an option is ITM, ATM, or OTM
        
        Parameters:
        -----------
        current_price : float
            Current price of the underlying
        strike_price : float
            Strike price of the option
        option_type : str
            Option type (CE or PE)
            
        Returns:
        --------
        str
            Option moneyness (ITM, ATM, OTM)
        """
        if option_type == 'CE':
            if current_price > strike_price:
                return 'ITM'
            elif current_price < strike_price:
                return 'OTM'
            else:
                return 'ATM'
        elif option_type == 'PE':
            if current_price < strike_price:
                return 'ITM'
            elif current_price > strike_price:
                return 'OTM'
            else:
                return 'ATM'
        else:
            return 'Unknown'
    
    @staticmethod
    def get_option_strikes(current_price, symbol=None, num_strikes=5, strike_interval=None):
        """
        Get a range of option strikes around the current price
        
        Parameters:
        -----------
        current_price : float
            Current price of the underlying
        symbol : str
            Symbol name for predefined intervals
        num_strikes : int
            Number of strikes to generate on each side
        strike_interval : float
            Strike price interval (if known)
            
        Returns:
        --------
        dict
            Dictionary with ITM, ATM, and OTM strikes for CE and PE
        """
        # Get ATM strike
        atm_strike = OptionHelpers.get_atm_strike(current_price, symbol, strike_interval)
        
        # Determine strike interval if not provided
        if strike_interval is None:
            if symbol in ['NIFTY', 'NIFTY50']:
                strike_interval = 50
            elif symbol in ['BANKNIFTY', 'NIFTYBANK']:
                strike_interval = 100
            elif symbol in ['FINNIFTY']:
                strike_interval = 50
            else:
                # For stocks, use percentage of price
                price_percent = current_price * 0.01
                
                if price_percent < 5:
                    strike_interval = 5
                elif price_percent < 10:
                    strike_interval = 10
                elif price_percent < 25:
                    strike_interval = 25
                elif price_percent < 50:
                    strike_interval = 50
                else:
                    strike_interval = 100
        
        # Generate strikes
        strikes = []
        for i in range(-num_strikes, num_strikes + 1):
            strikes.append(atm_strike + (i * strike_interval))
        
        # Categorize strikes
        ce_itm = []
        ce_otm = []
        pe_itm = []
        pe_otm = []
        
        for strike in strikes:
            if strike < current_price:
                ce_itm.append(strike)
                pe_otm.append(strike)
            elif strike > current_price:
                ce_otm.append(strike)
                pe_itm.append(strike)
        
        return {
            'ATM': atm_strike,
            'CE': {
                'ITM': sorted(ce_itm, reverse=True),
                'OTM': sorted(ce_otm)
            },
            'PE': {
                'ITM': sorted(pe_itm),
                'OTM': sorted(pe_otm, reverse=True)
            }
        }
    
    @staticmethod
    def get_expiry_date(symbol_type='index', reference_date=None):
        """
        Get the appropriate expiry date
        
        Parameters:
        -----------
        symbol_type : str
            Symbol type (index or equity)
        reference_date : datetime
            Reference date (defaults to current date)
            
        Returns:
        --------
        datetime
            Expiry date
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        if symbol_type == 'index':
            # For indexes, get the nearest weekly expiry (usually Thursday)
            days_to_thursday = (3 - reference_date.weekday()) % 7
            
            # If today is Thursday and it's past market close, get next week
            if days_to_thursday == 0 and reference_date.hour >= 15:
                days_to_thursday = 7
            
            expiry_date = reference_date + timedelta(days=days_to_thursday)
        else:
            # For equities, get the monthly expiry (last Thursday of the month)
            
            # Get the last day of the current month
            if reference_date.month == 12:
                last_day = datetime(reference_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(reference_date.year, reference_date.month + 1, 1) - timedelta(days=1)
            
            # Find the last Thursday
            days_to_subtract = (last_day.weekday() - 3) % 7
            last_thursday = last_day - timedelta(days=days_to_subtract)
            
            # If the last Thursday has passed, use the last Thursday of next month
            if last_thursday < reference_date:
                if reference_date.month == 12:
                    last_day = datetime(reference_date.year + 1, 2, 1) - timedelta(days=1)
                else:
                    last_day = datetime(reference_date.year, reference_date.month + 2, 1) - timedelta(days=1)
                
                days_to_subtract = (last_day.weekday() - 3) % 7
                last_thursday = last_day - timedelta(days=days_to_subtract)
            
            expiry_date = last_thursday
        
        return expiry_date
    
    @staticmethod
    def format_expiry_date(expiry_date, format_string="%d%b"):
        """
        Format expiry date according to broker requirements
        
        Parameters:
        -----------
        expiry_date : datetime
            Expiry date
        format_string : str
            Format string for the date
            
        Returns:
        --------
        str
            Formatted expiry date string
        """
        return expiry_date.strftime(format_string).upper()
    
    @staticmethod
    def calculate_intrinsic_value(current_price, strike_price, option_type):
        """
        Calculate intrinsic value of an option
        
        Parameters:
        -----------
        current_price : float
            Current price of the underlying
        strike_price : float
            Strike price of the option
        option_type : str
            Option type (CE or PE)
            
        Returns:
        --------
        float
            Intrinsic value
        """
        if option_type == 'CE':
            return max(0, current_price - strike_price)
        elif option_type == 'PE':
            return max(0, strike_price - current_price)
        else:
            return 0
    
    @staticmethod
    def build_option_symbol(underlying, expiry_date, strike_price, option_type, exchange_format='nse'):
        """
        Build option symbol according to exchange format
        
        Parameters:
        -----------
        underlying : str
            Underlying symbol
        expiry_date : datetime or str
            Expiry date or formatted string
        strike_price : float
            Strike price
        option_type : str
            Option type (CE or PE)
        exchange_format : str
            Exchange format ('nse', 'nfo', 'mcx', etc.)
            
        Returns:
        --------
        str
            Formatted option symbol
        """
        # Format expiry date if it's a datetime object
        if isinstance(expiry_date, datetime):
            if exchange_format == 'nse':
                expiry_str = expiry_date.strftime("%d%b").upper()
            else:
                expiry_str = expiry_date.strftime("%d%b%y").upper()
        else:
            expiry_str = expiry_date
        
        # Format strike price
        strike_str = str(int(strike_price)) if strike_price.is_integer() else str(strike_price)
        
        # Build symbol based on exchange format
        if exchange_format == 'nse':
            return f"{underlying}{expiry_str}{strike_str}{option_type}"
        elif exchange_format == 'nfo':
            return f"{underlying}{expiry_str}{strike_str}{option_type}"
        else:
            # Generic format
            return f"{underlying}-{expiry_str}-{strike_str}-{option_type}"