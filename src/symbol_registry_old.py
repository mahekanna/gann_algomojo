# -*- coding: utf-8 -*-
"""
Created on Fri Mar 14 00:28:15 2025

@author: mahes
"""

# src/symbol_registry.py

import os
import json
import logging
import re
from datetime import datetime, timedelta

class SymbolRegistry:
    """
    Dynamic symbol registry that handles mappings between different platforms
    without hardcoding values
    """
    
    def __init__(self, config_dir="config"):
        """
        Initialize the symbol registry
        
        Parameters:
        -----------
        config_dir : str
            Directory containing configuration files
        """
        self.logger = logging.getLogger(__name__)
        self.config_dir = config_dir
        self.symbols = {}
        self.mapping_rules = []
        
        # Load configurations
        self._load_symbols()
        self._load_mapping_rules()
    
    def _load_symbols(self):
        """Load symbols from configuration file"""
        symbols_file = os.path.join(self.config_dir, "symbols.json")
        
        if not os.path.exists(symbols_file):
            self.logger.warning(f"Symbols file not found: {symbols_file}")
            return
        
        try:
            with open(symbols_file, 'r') as f:
                data = json.load(f)
                
            if "symbols" in data and isinstance(data["symbols"], list):
                for symbol_info in data["symbols"]:
                    symbol = symbol_info.get("symbol", "")
                    if symbol:
                        self.symbols[symbol] = symbol_info
                
                self.logger.info(f"Loaded {len(self.symbols)} symbols from configuration")
            else:
                self.logger.warning("Invalid symbols file format")
                
        except Exception as e:
            self.logger.error(f"Error loading symbols: {e}")
    
    def _load_mapping_rules(self):
        """Load symbol mapping rules"""
        rules_file = os.path.join(self.config_dir, "symbol_mapping_rules.json")
        
        if not os.path.exists(rules_file):
            self.logger.warning(f"Mapping rules file not found: {rules_file}")
            return
        
        try:
            with open(rules_file, 'r') as f:
                data = json.load(f)
                
            if "rules" in data and isinstance(data["rules"], list):
                self.mapping_rules = data["rules"]
                self.logger.info(f"Loaded {len(self.mapping_rules)} mapping rules")
            else:
                self.logger.warning("Invalid mapping rules file format")
                
        except Exception as e:
            self.logger.error(f"Error loading mapping rules: {e}")
    
    def get_symbol_info(self, symbol):
        """
        Get information for a symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol identifier
            
        Returns:
        --------
        dict
            Symbol information or None if not found
        """
        # First try direct lookup
        if symbol in self.symbols:
            return self.symbols[symbol]
        
        # If not found directly, try looking up by tv_symbol or algomojo_symbol
        for sym_key, sym_info in self.symbols.items():
            if sym_info.get("tv_symbol") == symbol or sym_info.get("algomojo_symbol") == symbol:
                return sym_info
        
        return None
    
    def get_all_symbols(self):
        """
        Get all registered symbols
        
        Returns:
        --------
        list
            List of symbol dictionaries
        """
        return list(self.symbols.values())
    
    def map_symbol(self, symbol, from_platform, to_platform):
        """
        Map a symbol from one platform format to another
        
        Parameters:
        -----------
        symbol : str
            Symbol in source platform format
        from_platform : str
            Source platform (e.g., 'tv', 'algomojo')
        to_platform : str
            Target platform (e.g., 'tv', 'algomojo')
            
        Returns:
        --------
        str
            Symbol in target platform format
        """
        # If platforms are the same, return as is
        if from_platform == to_platform:
            return symbol
        
        # Check for exact mapping in symbol info
        for symbol_info in self.symbols.values():
            source_field = f"{from_platform}_symbol"
            target_field = f"{to_platform}_symbol"
            
            if symbol_info.get(source_field) == symbol and symbol_info.get(target_field):
                return symbol_info.get(target_field)
        
        # Try to determine symbol type if not found in registry
        symbol_type = self._determine_symbol_type(symbol)
        
        # Apply mapping rules
        for rule in self.mapping_rules:
            rule_from = rule.get("from")
            rule_to = rule.get("to")
            pattern = rule.get("pattern")
            replacement = rule.get("replacement")
            rule_type = rule.get("apply_to", "any")
            
            if rule_from == from_platform and rule_to == to_platform:
                # Skip if rule is for specific type and doesn't match
                if rule_type != "any" and rule_type != symbol_type:
                    continue
                
                if rule.get("use_regex", False):
                    try:
                        # Apply regex replacement
                        result = re.sub(pattern, replacement, symbol)
                        if result != symbol:  # Only return if something changed
                            self.logger.debug(f"Mapped {symbol} to {result} using regex rule")
                            return result
                    except Exception as e:
                        self.logger.error(f"Regex error: {e}")
                elif pattern in symbol:
                    # Simple string replacement
                    result = symbol.replace(pattern, replacement)
                    if result != symbol:  # Only return if something changed
                        self.logger.debug(f"Mapped {symbol} to {result} using string rule")
                        return result
        
        # Apply default mapping rules if no specific rule matched
        if from_platform == "tv" and to_platform == "algomojo":
            # Default TV to AlgoMojo
            if symbol_type == "equity" and not symbol.endswith("-EQ"):
                return f"{symbol}-EQ"
            elif symbol_type == "index" and not symbol.endswith("-I"):
                return f"{symbol}-I"
        elif from_platform == "algomojo" and to_platform == "tv":
            # Default AlgoMojo to TV
            if symbol.endswith("-EQ"):
                return symbol[:-3]
            elif symbol.endswith("-I"):
                return symbol[:-2]
        
        # If no mapping found, log warning and return original
        self.logger.warning(f"No mapping found for {symbol} from {from_platform} to {to_platform}")
        return symbol
    
    def _determine_symbol_type(self, symbol):
        """
        Determine the symbol type based on characteristics
        
        Parameters:
        -----------
        symbol : str
            Symbol to analyze
            
        Returns:
        --------
        str
            Symbol type ('equity', 'index', 'option', 'commodity')
        """
        # Check for known indices
        if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"] or symbol.endswith("-I"):
            return "index"
        
        # Check for options
        if "CE" in symbol or "PE" in symbol or "-CE" in symbol or "-PE" in symbol:
            return "option"
        
        # Check for commodities
        if symbol.endswith("1!") or symbol.startswith("MCX:") or "FUT" in symbol:
            return "commodity"
        
        # Check for equities with -EQ suffix
        if symbol.endswith("-EQ"):
            return "equity"
        
        # Default to equity for simple symbols
        if symbol.isalpha():
            return "equity"
        
        # Unknown
        return "unknown"
    
    def get_nearest_strike(self, symbol, price, round_up=False):
        """
        Get the nearest option strike price
        
        Parameters:
        -----------
        symbol : str
            Symbol name
        price : float
            Current price
        round_up : bool
            Whether to round up (True) or down (False)
            
        Returns:
        --------
        float
            Nearest strike price
        """
        # Get symbol info to find specific strike interval
        symbol_info = self.get_symbol_info(symbol)
        
        # Default strike intervals
        if symbol in ["NIFTY", "NIFTY50"] or (symbol_info and symbol_info.get("symbol") in ["NIFTY", "NIFTY50"]):
            interval = 50
        elif symbol in ["BANKNIFTY", "NIFTYBANK"] or (symbol_info and symbol_info.get("symbol") in ["BANKNIFTY", "NIFTYBANK"]):
            interval = 100
        elif symbol in ["FINNIFTY"] or (symbol_info and symbol_info.get("symbol") in ["FINNIFTY"]):
            interval = 50
        elif symbol in ["CRUDEOIL"] or (symbol_info and symbol_info.get("symbol") in ["CRUDEOIL"]):
            interval = 50  # Example interval for crude oil
        elif symbol in ["GOLD"] or (symbol_info and symbol_info.get("symbol") in ["GOLD"]):
            interval = 100  # Example interval for gold
        else:
            # For stocks, use percentage of price
            price_percent = price * 0.01
            
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
            return round(price / interval + 0.5) * interval  # Round up
        else:
            return round(price / interval) * interval  # Round to nearest
    
    def get_expiry_date(self, symbol_type="equity", reference_date=None):
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
        str
            Expiry date formatted for trading platform
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        if symbol_type == "index":
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
        
        # Format the expiry date according to broker requirements (e.g., "23JUN")
        return expiry_date.strftime("%d%b").upper()
    
    def get_commodity_expiry(self, symbol, current_date=None):
        """
        Get the current active commodity expiry
        
        Parameters:
        -----------
        symbol : str
            Commodity symbol
        current_date : datetime
            Reference date (defaults to current date)
            
        Returns:
        --------
        str
            Expiry date in the format required for trading platform
        """
        if current_date is None:
            current_date = datetime.now()
        
        # Commodity-specific expiry calendar
        # Different commodities have different expiry patterns
        commodity_expiry_calendar = {
            "CRUDEOIL": {
                "day_pattern": "19",  # Usually expires on 19th
                "month_offset": 0     # Current month
            },
            "GOLD": {
                "day_pattern": "5",   # Usually expires on 5th 
                "month_offset": 1     # Next month
            },
            "SILVER": {
                "day_pattern": "5",   # Usually expires on 5th
                "month_offset": 1     # Next month
            },
            # Add more commodities as needed
        }
        
        # Get base symbol without suffixes
        base_symbol = symbol.split('-')[0].split(':')[-1]
        
        if base_symbol in commodity_expiry_calendar:
            pattern = commodity_expiry_calendar[base_symbol]
            
            # Calculate expiry month
            expiry_month = current_date.month + pattern["month_offset"]
            expiry_year = current_date.year
            
            if expiry_month > 12:
                expiry_month -= 12
                expiry_year += 1
            
            # Determine day based on pattern
            day_pattern = pattern["day_pattern"]
            
            if day_pattern.isdigit():
                # Fixed day of month
                day = int(day_pattern)
            else:
                # Complex pattern (like "last Thursday")
                # Implementation would go here
                day = 15  # Default fallback
            
            # Format expiry date
            expiry_date = datetime(expiry_year, expiry_month, day)
            
            # Format according to trading platform requirements (e.g., "JUN23")
            return expiry_date.strftime("%d%b").upper()
        
        # Default fallback - current month
        next_month = current_date.month + 1
        next_year = current_date.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        
        last_day = (datetime(next_year, next_month, 1) - timedelta(days=1)).day
        expiry_date = datetime(current_date.year, current_date.month, last_day)
        
        return expiry_date.strftime("%d%b").upper()