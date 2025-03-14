# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 21:21:20 2025

@author: mahes
"""

# src/gann_calculator.py

import math
import logging
import numpy as np
import pandas as pd

class GannCalculator:
    """
    Implements the Gann Square of 9 calculation for trading signals
    """
    
    def __init__(self, gann_params):
        """
        Initialize the Gann calculator with parameters
        
        Parameters:
        -----------
        gann_params : dict
            Dictionary containing Gann Square of 9 parameters
            - increments: list of increments for different angles
            - num_values: number of values to generate per angle
            - buffer_percentage: percentage buffer for stoploss calculation
        """
        self.logger = logging.getLogger(__name__)
        self.increments = gann_params.get('increments', [0.125, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25])
        self.num_values = gann_params.get('num_values', 20)
        self.buffer_percentage = gann_params.get('buffer_percentage', 0.002)
        self.include_lower = gann_params.get('include_lower', True)
        
    def calculate(self, price):
        """
        Calculate Gann Square of 9 levels for a given price
        
        Parameters:
        -----------
        price : float
            Price to calculate Gann levels for (typically previous candle close)
            
        Returns:
        --------
        dict
            Dictionary containing Gann levels and targets
        """
        try:
            self.logger.info(f"Calculating Gann Square of 9 for price: {price}")
            
            # Generate Gann values for different angles
            gann_values = self._gann_square_of_9(price)
            
            # Find buy above and sell below levels (0° angle)
            buy_level_0, sell_level_0 = self._find_buy_sell_levels(price, {'0°': gann_values['0°']})
            
            if not buy_level_0 or not sell_level_0:
                self.logger.warning(f"Could not find buy/sell levels for price {price}")
                return None
            
            # Get targets from various angles
            buy_targets, sell_targets = self._get_unique_targets_from_angles(
                buy_level_0[1],
                gann_values,
                8,  # Number of target levels
                price,
                sell_level_0[1]
            )
            
            # Calculate stoploss levels
            long_stoploss, short_stoploss = self._calculate_stoploss(
                buy_level_0, 
                sell_level_0, 
                self.buffer_percentage
            )
            
            # Prepare results
            results = {
                "price": price,
                "buy_above": buy_level_0[1],
                "sell_below": sell_level_0[1],
                "buy_targets": [value for _, value in buy_targets],
                "sell_targets": [value for _, value in sell_targets],
                "stoploss_long": long_stoploss,
                "stoploss_short": short_stoploss,
                "gann_values": gann_values
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in Gann calculation: {e}")
            return None
    
    def _gann_square_of_9(self, price):
        """
        Generates Gann Square of 9 levels for different angles.
        
        Original implementation from the provided code.
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
    
    def _find_buy_sell_levels(self, price, gann_values):
        """
        Finds the nearest Buy and Sell levels from the 0° angle.
        
        Original implementation from the provided code.
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
    
    def _get_unique_targets_from_angles(self, entry_value, gann_values, num_levels, current_price, sell_below_value):
        """
        Fetch unique buy and sell targets, ensuring unique buy targets per angle.
        
        Original implementation from the provided code.
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
    
    def _calculate_stoploss(self, buy_above, sell_below, buffer_percentage):
        """
        Calculate stoploss for long and short trades.
        
        Original implementation from the provided code.
        """
        long_stoploss = round(sell_below[1] * (1 - buffer_percentage), 2) if sell_below else None
        short_stoploss = round(buy_above[1] * (1 + buffer_percentage), 2) if buy_above else None
        return long_stoploss, short_stoploss
    
    def generate_visualization(self, price):
        """
        Generate visualization data for Gann levels (for UI display)
        
        Parameters:
        -----------
        price : float
            Price to calculate Gann levels for
            
        Returns:
        --------
        dict
            Dictionary containing visualization data
        """
        try:
            # Calculate Gann levels
            results = self.calculate(price)
            if not results:
                return None
                
            # Prepare visualization data
            visualization_data = {
                "price": price,
                "angles": [],
                "buy_above": results["buy_above"],
                "sell_below": results["sell_below"],
                "buy_targets": results["buy_targets"][:3],
                "sell_targets": results["sell_targets"][:3]
            }
            
            # Format angle data for visualization
            for angle in ['0°', '45°', '90°', '135°', '180°', '225°', '270°', '315°']:
                angle_data = {
                    "angle": angle,
                    "values": results["gann_values"][angle][:10]  # First 10 values for display
                }
                visualization_data["angles"].append(angle_data)
                
            return visualization_data
            
        except Exception as e:
            self.logger.error(f"Error generating visualization: {e}")
            return None