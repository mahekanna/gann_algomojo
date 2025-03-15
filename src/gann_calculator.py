# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 23:32:06 2025

@author: mahes
"""

# -*- coding: utf-8 -*-
"""
Gann Square of 9 Calculator

This module implements W.D. Gann's Square of 9 technique for price level identification
"""

import math
import logging
from typing import Dict, List, Tuple, Any, Optional

class GannCalculator:
    """
    Implements Gann Square of 9 calculations for trading
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Initialize the Gann calculator with parameters
        
        Parameters:
        -----------
        params : dict
            Parameters for Gann calculations including:
            - increments: list of float
                Increment values for different angles
            - num_values: int
                Number of values to generate
            - buffer_percentage: float
                Buffer percentage for stoploss calculation
            - include_lower: bool
                Whether to include values below the central value
        """
        self.logger = logging.getLogger(__name__)
        
        # Set default parameters
        self.increments = params.get('increments', [0.125, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25])
        self.num_values = params.get('num_values', 20)
        self.buffer_percentage = params.get('buffer_percentage', 0.002)
        self.include_lower = params.get('include_lower', True)
        
        self.logger.info("Gann Calculator initialized with increments: {}".format(self.increments))
    
    def calculate(self, price: float) -> Dict[str, Any]:
        """
        Calculate Gann Square of 9 levels for a given price
        
        Parameters:
        -----------
        price : float
            Price to analyze
            
        Returns:
        --------
        dict
            Calculated Gann levels
        """
        if price <= 0:
            self.logger.error("Invalid price for Gann calculation: {}".format(price))
            return {}
        
        try:
            # Calculate Gann values
            gann_values = self._gann_square_of_9(price)
            
            # Find buy/sell levels
            buy_level, sell_level = self._find_buy_sell_levels(price, gann_values)
            
            if not buy_level or not sell_level:
                self.logger.warning("Could not find buy/sell levels for price {}".format(price))
                return {}
            
            # Get buy and sell targets
            buy_targets, sell_targets = self._get_unique_targets_from_angles(
                buy_level[1],
                gann_values,
                3,  # Number of target levels
                price,
                sell_level[1]
            )
            
            # Calculate stoploss levels
            stoploss_long, stoploss_short = self._calculate_stoploss(
                buy_level, 
                sell_level, 
                self.buffer_percentage
            )
            
            # Format targets for return
            buy_targets_formatted = [{"angle": angle, "price": price} for angle, price in buy_targets]
            sell_targets_formatted = [{"angle": angle, "price": price} for angle, price in sell_targets]
            
            return {
                "input_price": price,
                "buy_above": buy_level[1],
                "sell_below": sell_level[1],
                "buy_targets": buy_targets_formatted,
                "sell_targets": sell_targets_formatted,
                "stoploss_long": stoploss_long,
                "stoploss_short": stoploss_short
            }
            
        except Exception as e:
            self.logger.error("Error in Gann calculation: {}".format(str(e)))
            return {}
    
    def _gann_square_of_9(self, price: float) -> Dict[str, List[float]]:
        """
        Generate Gann Square of 9 levels for different angles
        
        Parameters:
        -----------
        price : float
            Price to analyze
            
        Returns:
        --------
        dict
            Dictionary with angles as keys and lists of values as values
        """
        gann_values = {}
        angles = ['0°', '45°', '90°', '135°', '180°', '225°', '270°', '315°']
        
        root = math.sqrt(price)
        base = math.floor(root)
        central_value = base * base
        
        for angle, increment in zip(angles, self.increments):
            gann_values[angle] = []
            is_cardinal = angle.replace('°', '').isdigit() and int(angle.replace('°', '')) % 90 == 0
            base_mult = 1.0 if is_cardinal else 1.125
            
            if self.include_lower:
                lower_count = self.num_values // 2
                for i in range(lower_count, 0, -1):
                    if is_cardinal:
                        val = base - (i * increment)
                        if val > 0:
                            squared = val * val
                            gann_values[angle].insert(0, round(squared, 2))
                    else:
                        val = base - (i * increment * base_mult)
                        if val > 0:
                            squared = val * val
                            gann_values[angle].insert(0, round(squared, 2))
            
            gann_values[angle].append(round(central_value, 2))
            
            for i in range(1, self.num_values + 1):
                if is_cardinal:
                    val = base + (i * increment)
                    squared = val * val
                else:
                    val = base + (i * increment * base_mult)
                    squared = val * val
                gann_values[angle].append(round(squared, 2))
        
        return gann_values
    
    def _find_buy_sell_levels(self, price: float, gann_values: Dict[str, List[float]]) -> Tuple[Tuple[str, float], Tuple[str, float]]:
        """
        Find the nearest Buy and Sell levels from the 0° angle
        
        Parameters:
        -----------
        price : float
            Current price
        gann_values : dict
            Gann Square of 9 values
            
        Returns:
        --------
        ((str, float), (str, float))
            ((buy_angle, buy_price), (sell_angle, sell_price))
        """
        buy_above = None
        sell_below = None
        closest_above = None
        closest_below = None
        
        if '0°' in gann_values:
            for value in gann_values['0°']:
                if value > price and (closest_above is None or value < closest_above):
                    closest_above = value
                    buy_above = ('0°', value)
                if value < price and (closest_below is None or value > closest_below):
                    closest_below = value
                    sell_below = ('0°', value)
        
        return buy_above, sell_below
    
    def _get_unique_targets_from_angles(self, entry_value: float, gann_values: Dict[str, List[float]], 
                                       num_levels: int, current_price: float, 
                                       sell_below_value: Optional[float] = None) -> Tuple[List[Tuple[str, float]], List[Tuple[str, float]]]:
        """
        Fetch unique buy and sell targets, ensuring unique buy targets per angle
        
        Parameters:
        -----------
        entry_value : float
            Entry value (buy_above)
        gann_values : dict
            Gann Square of 9 values
        num_levels : int
            Number of target levels to return
        current_price : float
            Current market price
        sell_below_value : float, optional
            Sell below value
            
        Returns:
        --------
        (list, list)
            (buy_targets, sell_targets)
        """
        angles = ['0°', '45°', '90°', '135°', '180°', '225°', '270°', '315°']
        buy_targets = []
        sell_targets = []
        used_values_buy = set()
        used_values_sell = set()
        
        # Buy targets: Ensure unique values, one per angle
        for angle in angles:
            values_above = [v for v in gann_values[angle] if v > entry_value and v not in used_values_buy]
            if values_above:
                closest_above = min(values_above)
                buy_targets.append((angle, closest_above))
                used_values_buy.add(closest_above)
        
        # Sell targets: Start with central value, then unique below sell_below_value
        if sell_below_value is not None:
            central_value = math.floor(math.sqrt(current_price)) ** 2
            if central_value < sell_below_value:
                sell_targets.append(('0°', central_value))
                used_values_sell.add(central_value)
            
            for angle in angles:
                values_below = [v for v in gann_values[angle] if v < sell_below_value and v not in used_values_sell]
                if values_below:
                    highest_below = max(values_below)
                    sell_targets.append((angle, highest_below))
                    used_values_sell.add(highest_below)
        
        # Sort and limit to num_levels
        buy_targets = sorted(buy_targets, key=lambda x: x[1])[:num_levels]
        sell_targets = sorted(sell_targets, key=lambda x: x[1], reverse=True)[:num_levels]
        
        return buy_targets, sell_targets
    
    def _calculate_stoploss(self, buy_above: Tuple[str, float], sell_below: Tuple[str, float], 
                          buffer_percentage: float) -> Tuple[float, float]:
        """
        Calculate stoploss for long and short trades
        
        Parameters:
        -----------
        buy_above : tuple
            (angle, price) for buy_above level
        sell_below : tuple
            (angle, price) for sell_below level
        buffer_percentage : float
            Buffer percentage for stoploss calculation
            
        Returns:
        --------
        (float, float)
            (long_stoploss, short_stoploss)
        """
        long_stoploss = round(sell_below[1] * (1 - buffer_percentage), 2) if sell_below else None
        short_stoploss = round(buy_above[1] * (1 + buffer_percentage), 2) if buy_above else None
        return long_stoploss, short_stoploss