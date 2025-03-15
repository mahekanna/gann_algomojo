# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 23:36:14 2025

@author: mahes
"""

# -*- coding: utf-8 -*-
"""
Symbol Registry

This module manages symbol information and mappings between different platforms
"""

import json
import logging
import re
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

class SymbolRegistry:
    """
    Registry for symbol information and conversions
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the symbol registry
        
        Parameters:
        -----------
        config_path : str or Path
            Path to configuration directory
        """
        self.logger = logging.getLogger(__name__)
        
        # Convert config_path to Path object if it's a string
        if isinstance(config_path, str):
            config_path = Path(config_path)
        
        self.config_path = config_path
        
        # Load symbol configuration
        self.symbols = self._load_symbols()
        
        # Load symbol mapping rules
        self.mapping_rules = self._load_mapping_rules()
        
        self.logger.info(f"Symbol registry initialized with {len(self.symbols)} symbols")
    
    def _load_symbols(self) -> Dict[str, Dict[str, Any]]:
        """
        Load symbol information from configuration
        
        Returns:
        --------
        dict
            Symbol information keyed by symbol name
        """
        try:
            symbols_file = self.config_path / "symbols.json"
            
            if not symbols_file.exists():
                self.logger.error("Symbols configuration file not found")
                return {}
            
            with open(symbols_file, 'r') as f:
                symbols_config = json.load(f)
            
            symbols_dict = {}
            
            for symbol_info in symbols_config.get('symbols', []):
                symbol = symbol_info.get('symbol')
                if symbol:
                    symbols_dict[symbol] = symbol_info
            
            return symbols_dict
            
        except Exception as e:
            self.logger.error(f"Error loading symbols: {e}")
            return {}
    
    def _load_mapping_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load symbol mapping rules from configuration
        
        Returns:
        --------
        dict
            Mapping rules grouped by direction
        """
        try:
            mapping_file = self.config_path / "symbol_mapping_rules.json"
            
            if not mapping_file.exists():
                self.logger.error("Symbol mapping rules file not found")
                return {}
            
            with open(mapping_file, 'r') as f:
                mapping_config = json.load(f)
            
            # Group rules by direction
            rules_by_direction = {}
            
            for rule in mapping_config.get('rules', []):
                direction = f"{rule.get('from')}_{rule.get('to')}"
                
                if direction not in rules_by_direction:
                    rules_by_direction[direction] = []
                
                rules_by_direction[direction].append(rule)
            
            return rules_by_direction
            
        except Exception as e:
            self.logger.error(f"Error loading mapping rules: {e}")
            return {}
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get information for a symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol name
            
        Returns:
        --------
        dict
            Symbol information
        """
        return self.symbols.get(symbol, {})
    
    def get_all_symbols(self) -> List[Dict[str, Any]]:
        """
        Get information for all symbols
        
        Returns:
        --------
        list
            List of symbol information
        """
        return list(self.symbols.values())
    
    def convert_symbol(self, symbol: str, from_platform: str, to_platform: str) -> str:
        """
        Convert a symbol from one platform to another
        
        Parameters:
        -----------
        symbol : str
            Symbol to convert
        from_platform : str
            Source platform ('tv' for TradingView, 'algomojo' for AlgoMojo)
        to_platform : str
            Target platform ('tv' for TradingView, 'algomojo' for AlgoMojo)
            
        Returns:
        --------
        str
            Converted symbol
        """
        # Check if the symbol exists in our registry with direct mapping
        symbol_info = self.get_symbol_info(symbol)
        
        if symbol_info:
            if from_platform == 'tv' and to_platform == 'algomojo':
                return symbol_info.get('algomojo_symbol', symbol)
            elif from_platform == 'algomojo' and to_platform == 'tv':
                return symbol_info.get('tv_symbol', symbol)
        
        # If not found in registry, apply conversion rules
        direction = f"{from_platform}_{to_platform}"
        rules = self.mapping_rules.get(direction, [])
        
        for rule in rules:
            pattern = rule.get('pattern', '')
            replacement = rule.get('replacement', '')
            use_regex = rule.get('use_regex', False)
            
            if use_regex:
                if re.match(pattern, symbol):
                    converted = re.sub(pattern, replacement, symbol)
                    return converted
            else:
                if symbol == pattern:
                    return replacement
        
        # If no conversion rule matched, return the original symbol
        return symbol
    
    def get_nearest_strike(self, symbol: str, price: float, round_up: bool = False) -> float:
        """
        Get the nearest strike price for an option
        
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
        symbol_info = self.get_symbol_info(symbol)
        
        # Get strike interval from symbol info or use default
        strike_interval = symbol_info.get('strike_interval', 100)
        
        # Calculate nearest strike
        if round_up:
            return math.ceil(price / strike_interval) * strike_interval
        else:
            return math.floor(price / strike_interval) * strike_interval
    
    def get_expiry_date(self, symbol_type: str) -> str:
        """
        Get the nearest expiry date for options
        
        Parameters:
        -----------
        symbol_type : str
            Type of symbol (equity, index, etc.)
            
        Returns:
        --------
        str
            Expiry date in format 'DDMMMYYYY'
        """
        # In a real implementation, you would fetch this from an API
        # For now, we'll calculate the next expiry date
        
        now = datetime.now()
        
        if symbol_type == 'index':
            # Weekly expiry - Thursday
            days_to_thursday = (3 - now.weekday()) % 7
            
            # If it's Thursday after market hours, go to next Thursday
            if days_to_thursday == 0 and now.hour >= 15:
                days_to_thursday = 7
            
            expiry_date = now + timedelta(days=days_to_thursday)
            
        else:  # equity
            # Monthly expiry - last Thursday of the month
            # Go to next month if we're in last week
            next_month = now.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)
            
            # Find last Thursday
            last_day = next_month - timedelta(days=1)
            last_thursday = last_day
            
            while last_thursday.weekday() != 3:  # 3 is Thursday
                last_thursday = last_thursday - timedelta(days=1)
            
            # If we're after the current month's last Thursday, use next month's
            current_month_last_thursday = last_thursday.replace(month=now.month)
            
            if now > current_month_last_thursday:
                expiry_date = last_thursday
            else:
                expiry_date = current_month_last_thursday
        
        return expiry_date.strftime('%d%b%Y').upper()
    
    def get_commodity_expiry(self, symbol: str) -> str:
        """
        Get the nearest expiry date for commodity futures
        
        Parameters:
        -----------
        symbol : str
            Commodity symbol
            
        Returns:
        --------
        str
            Expiry date in format 'DDMMMYYYY'
        """
        # In a real implementation, you would fetch this from an API
        # For now, return current month's last day
        now = datetime.now()
        next_month = now.replace(day=1) + timedelta(days=32)
        last_day = next_month.replace(day=1) - timedelta(days=1)
        
        return last_day.strftime('%d%b%Y').upper()