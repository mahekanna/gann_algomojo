# -*- coding: utf-8 -*-
"""
Created on Wed Mar 12 22:57:04 2025

@author: mahes
"""

# src/symbol_registry.py

# -*- coding: utf-8 -*-
"""
Created on Wed Mar 13 10:15:37 2025

@author: mahes
"""

# src/symbol_registry.py

import json
import re
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta

class SymbolRegistry:
    """
    Manages symbol mappings between different platforms (TradingView, AlgoMojo, etc.)
    """
    
    def __init__(self, config_dir="config"):
        """
        Initialize the symbol registry with symbols from configuration
        
        Parameters:
        -----------
        config_dir : str
            Directory containing configuration files
        """
        self.logger = logging.getLogger(__name__)
        self.config_dir = Path(config_dir)
        
        # Load symbols configuration
        self.symbols = {}
        self.load_symbols()
        
        # Load mapping rules
        self.mapping_rules = {}
        self.load_mapping_rules()
    
    def load_symbols(self):
        """Load symbols from configuration file"""
        try:
            symbols_file = self.config_dir / "symbols.json"
            if symbols_file.exists():
                with open(symbols_file, 'r') as f:
                    config = json.load(f)
                    
                    if "symbols" in config and isinstance(config["symbols"], list):
                        for symbol_info in config["symbols"]:
                            if "symbol" in symbol_info:
                                self.symbols[symbol_info["symbol"]] = symbol_info
                
                self.logger.info(f"Loaded {len(self.symbols)} symbols from configuration")
            else:
                self.logger.warning(f"Symbols configuration file not found: {symbols_file}")
        except Exception as e:
            self.logger.error(f"Error loading symbols configuration: {e}")
    
    def load_mapping_rules(self):
        """Load symbol mapping rules from configuration file"""
        try:
            rules_file = self.config_dir / "mapping_rules.json"
            if rules_file.exists():
                with open(rules_file, 'r') as f:
                    config = json.load(f)
                    
                    if "rules" in config and isinstance(config["rules"], list):
                        # Group rules by from->to platform pairs
                        for rule in config["rules"]:
                            from_platform = rule.get("from", "")
                            to_platform = rule.get("to", "")
                            
                            if from_platform and to_platform:
                                key = f"{from_platform}->{to_platform}"
                                
                                if key not in self.mapping_rules:
                                    self.mapping_rules[key] = []
                                
                                self.mapping_rules[key].append(rule)
                
                self.logger.info(f"Loaded {sum(len(rules) for rules in self.mapping_rules.values())} mapping rules")
            else:
                self.logger.info(f"Symbol mapping rules file not found: {rules_file}, using default rules")
                # Set up default rules if file doesn't exist
                self._setup_default_rules()
        except Exception as e:
            self.logger.error(f"Error loading mapping rules: {e}")
            # Setup default rules as fallback
            self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default mapping rules"""
        # TradingView to AlgoMojo rules
        tv_to_am_rules = [
            {
                "pattern": r"^([A-Z]+)$",
                "replacement": r"\1-EQ",
                "description": "Convert simple equity symbol to AlgoMojo format",
                "use_regex": True,
                "apply_to": "equity"
            },
            {
                "pattern": r"^(NIFTY|BANKNIFTY|FINNIFTY)$", 
                "replacement": r"\1-I",
                "description": "Convert index symbol to AlgoMojo format",
                "use_regex": True,
                "apply_to": "index"
            },
            {
                "pattern": r"([A-Z]+)(\d{2})([A-Z]{3})(\d+)(CE|PE)",
                "replacement": r"\1-\2\3-\4-\5",
                "description": "Convert TradingView option to AlgoMojo format",
                "use_regex": True,
                "apply_to": "option"
            },
            {
                "pattern": r"([A-Z]+)1!",
                "replacement": r"\1-FUT",
                "description": "Convert TradingView commodity futures to AlgoMojo format",
                "use_regex": True,
                "apply_to": "commodity"
            },
            {
                "pattern": r"MCX:([A-Z]+)",
                "replacement": r"\1-FUT",
                "description": "Convert TradingView MCX commodities to AlgoMojo format",
                "use_regex": True,
                "apply_to": "commodity"
            }
        ]
        
        # AlgoMojo to TradingView rules
        am_to_tv_rules = [
            {
                "pattern": r"^([A-Z]+)-EQ$",
                "replacement": r"\1",
                "description": "Convert AlgoMojo equity to TradingView format",
                "use_regex": True,
                "apply_to": "equity"
            },
            {
                "pattern": r"^([A-Z]+)-I$",
                "replacement": r"\1",
                "description": "Convert AlgoMojo index to TradingView format",
                "use_regex": True,
                "apply_to": "index"
            },
            {
                "pattern": r"([A-Z]+)-(\d{2})([A-Z]{3})-(\d+)-(CE|PE)",
                "replacement": r"\1\2\3\4\5",
                "description": "Convert AlgoMojo option to TradingView format",
                "use_regex": True,
                "apply_to": "option"
            },
            {
                "pattern": r"([A-Z]+)-FUT",
                "replacement": r"\11!",
                "description": "Convert AlgoMojo commodity futures to TradingView format",
                "use_regex": True,
                "apply_to": "commodity"
            },
            {
                "pattern": r"([A-Z]+)MINI-([0-9A-Z]+)",
                "replacement": r"\1MINI1!",
                "description": "Convert AlgoMojo mini commodity contracts to TradingView format",
                "use_regex": True,
                "apply_to": "commodity"
            }
        ]
        
        # Store rules
        self.mapping_rules["tv->algomojo"] = tv_to_am_rules
        self.mapping_rules["algomojo->tv"] = am_to_tv_rules
    
    def map_symbol(self, symbol, from_platform, to_platform):
        """
        Map a symbol from one platform format to another
        
        Parameters:
        -----------
        symbol : str
            Symbol to map
        from_platform : str
            Source platform ("tv", "algomojo", etc.)
        to_platform : str
            Target platform ("tv", "algomojo", etc.)
            
        Returns:
        --------
        str
            Mapped symbol
        """
        # If platforms are the same, return the original symbol
        if from_platform == to_platform:
            return symbol
        
        # Check if we have a direct mapping in symbols config
        for sym_info in self.symbols.values():
            from_field = f"{from_platform}_symbol"
            to_field = f"{to_platform}_symbol"
            
            if from_field in sym_info and to_field in sym_info:
                if sym_info[from_field] == symbol:
                    return sym_info[to_field]
        
        # Apply mapping rules
        key = f"{from_platform}->{to_platform}"
        if key in self.mapping_rules:
            rules = self.mapping_rules[key]
            
            # Try to find symbol info to determine type
            symbol_type = None
            for sym_info in self.symbols.values():
                if from_platform + "_symbol" in sym_info and sym_info[from_platform + "_symbol"] == symbol:
                    symbol_type = sym_info.get("type")
                    break
            
            # Apply rules
            for rule in rules:
                apply_to = rule.get("apply_to")
                
                # Skip rule if it's for a specific type that doesn't match
                if symbol_type and apply_to and symbol_type != apply_to:
                    continue
                
                if rule.get("use_regex", False):
                    pattern = rule["pattern"]
                    replacement = rule["replacement"]
                    
                    try:
                        mapped_symbol = re.sub(pattern, replacement, symbol)
                        
                        # If the symbol was changed, return it
                        if mapped_symbol != symbol:
                            return mapped_symbol
                    except Exception as e:
                        self.logger.error(f"Error applying regex rule: {e}")
                else:
                    # Exact match rule
                    pattern = rule["pattern"]
                    replacement = rule["replacement"]
                    
                    if symbol == pattern:
                        return replacement
        
        # If no mapping found, return the original
        return symbol
    
    def get_option_info(self, underlying, option_type="CE", strike_price=None, expiry_date=None):
        """
        Get information for constructing option symbols
        
        Parameters:
        -----------
        underlying : str
            Underlying symbol
        option_type : str
            "CE" or "PE"
        strike_price : float
            Strike price (optional)
        expiry_date : str
            Expiry date (optional)
            
        Returns:
        --------
        dict
            Option information
        """
        # Get symbol info if available
        symbol_info = None
        for info in self.symbols.values():
            if info.get("symbol") == underlying:
                symbol_info = info
                break
        
        # If not found, use defaults
        if not symbol_info:
            symbol_info = {
                "symbol": underlying,
                "type": "equity" if underlying not in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else "index",
                "option_lot_size": 50
            }
        
        # Get current price if strike price not provided
        # In a real implementation, this would fetch from a data source
        if strike_price is None:
            strike_price = 0  # Placeholder
        
        # Get expiry date if not provided
        if expiry_date is None:
            if symbol_info.get("type") == "commodity":
                expiry_date = self.get_commodity_expiry(underlying)
            else:
                expiry_date = self.get_expiry_date(symbol_info.get("type", "equity"))
        
        # Construct option info
        option_info = {
            "underlying": underlying,
            "option_type": option_type,
            "strike_price": strike_price,
            "expiry_date": expiry_date,
            "lot_size": symbol_info.get("option_lot_size", 50),
            "tv_symbol": f"{underlying}{expiry_date}{int(strike_price)}{option_type}",
            "algomojo_symbol": f"{underlying}-{expiry_date}-{int(strike_price)}-{option_type}"
        }
        
        return option_info
    
    def get_expiry_date(self, symbol_type="equity", reference_date=None):
        """
        Get the appropriate expiry date based on symbol type
        
        Parameters:
        -----------
        symbol_type : str
            Symbol type (equity, index, etc.)
        reference_date : datetime
            Reference date (defaults to current date)
            
        Returns:
        --------
        str
            Expiry date in the format required by brokers
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
        
        # Format the expiry date according to broker requirements
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
            Expiry date in the format required by brokers
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
            
            # Format according to broker requirements (adjust as needed)
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
    
    def get_nearest_strike(self, symbol, current_price, round_up=False):
        """
        Get the nearest strike price for an option
        
        Parameters:
        -----------
        symbol : str
            Underlying symbol
        current_price : float
            Current price
        round_up : bool
            Whether to round up (True) or down (False)
            
        Returns:
        --------
        float
            Nearest strike price
        """
        # Determine strike interval based on symbol
        if symbol in ['NIFTY', 'NIFTY50']:
            interval = 50
        elif symbol in ['BANKNIFTY', 'NIFTYBANK']:
            interval = 100
        elif symbol in ['FINNIFTY']:
            interval = 50
        elif symbol in ['CRUDEOIL']:
            interval = 50  # Adjust based on actual MCX intervals
        elif symbol in ['GOLD']:
            interval = 100  # Adjust based on actual MCX intervals
        elif symbol in ['SILVER']:
            interval = 100  # Adjust based on actual MCX intervals
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
            return (current_price // interval + 1) * interval
        else:
            return (current_price // interval) * interval
    
    def save_symbols(self):
        """Save symbols configuration to file"""
        try:
            symbols_file = self.config_dir / "symbols.json"
            
            # Ensure directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(symbols_file, 'w') as f:
                json.dump({"symbols": list(self.symbols.values())}, f, indent=2)
            
            self.logger.info(f"Saved {len(self.symbols)} symbols to configuration")
        except Exception as e:
            self.logger.error(f"Error saving symbols configuration: {e}")
    
    def save_mapping_rules(self):
        """Save mapping rules to file"""
        try:
            rules_file = self.config_dir / "mapping_rules.json"
            
            # Ensure directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Flatten rules
            all_rules = []
            for key, rules in self.mapping_rules.items():
                from_platform, to_platform = key.split("->")
                
                for rule in rules:
                    rule_copy = rule.copy()
                    rule_copy["from"] = from_platform
                    rule_copy["to"] = to_platform
                    all_rules.append(rule_copy)
            
            with open(rules_file, 'w') as f:
                json.dump({"rules": all_rules}, f, indent=2)
            
            self.logger.info(f"Saved {len(all_rules)} mapping rules to configuration")
        except Exception as e:
            self.logger.error(f"Error saving mapping rules: {e}")
    
    def add_symbol(self, symbol_info):
        """
        Add or update a symbol in the registry
        
        Parameters:
        -----------
        symbol_info : dict
            Symbol information
            
        Returns:
        --------
        bool
            Success status
        """
        try:
            if "symbol" in symbol_info:
                self.symbols[symbol_info["symbol"]] = symbol_info
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error adding symbol: {e}")
            return False
    
    def remove_symbol(self, symbol):
        """
        Remove a symbol from the registry
        
        Parameters:
        -----------
        symbol : str
            Symbol to remove
            
        Returns:
        --------
        bool
            Success status
        """
        try:
            if symbol in self.symbols:
                del self.symbols[symbol]
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing symbol: {e}")
            return False
    
    def get_all_symbols(self):
        """
        Get all symbols in the registry
        
        Returns:
        --------
        list
            List of symbol information dictionaries
        """
        return list(self.symbols.values())
    
    def get_symbol_info(self, symbol):
        """
        Get information for a specific symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol to look up
            
        Returns:
        --------
        dict
            Symbol information or None if not found
        """
        return self.symbols.get(symbol)
    
    def get_symbols_by_type(self, symbol_type):
        """
        Get all symbols of a specific type
        
        Parameters:
        -----------
        symbol_type : str
            Symbol type (equity, index, commodity, etc.)
            
        Returns:
        --------
        list
            List of symbol information dictionaries
        """
        return [info for info in self.symbols.values() if info.get("type") == symbol_type]