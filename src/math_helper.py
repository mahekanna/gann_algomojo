# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 23:05:58 2025

@author: mahes
"""

# src/math_helper.py

import math
import numpy as np

class MathHelper:
    """
    Helper class for mathematical calculations used in Gann analysis
    """
    
    @staticmethod
    def square_root(number):
        """
        Calculate the square root of a number
        
        Parameters:
        -----------
        number : float
            Input number
            
        Returns:
        --------
        float
            Square root of the number
        """
        return math.sqrt(number)
    
    @staticmethod
    def floor_sqrt(number):
        """
        Calculate the floor of the square root of a number
        
        Parameters:
        -----------
        number : float
            Input number
            
        Returns:
        --------
        int
            Floor of the square root
        """
        return math.floor(math.sqrt(number))
    
    @staticmethod
    def ceil_sqrt(number):
        """
        Calculate the ceiling of the square root of a number
        
        Parameters:
        -----------
        number : float
            Input number
            
        Returns:
        --------
        int
            Ceiling of the square root
        """
        return math.ceil(math.sqrt(number))
    
    @staticmethod
    def square(number):
        """
        Calculate the square of a number
        
        Parameters:
        -----------
        number : float
            Input number
            
        Returns:
        --------
        float
            Square of the number
        """
        return number * number
    
    @staticmethod
    def get_nearest_cardinal_angle_value(base, value, increment):
        """
        Get the nearest cardinal angle value based on increment
        
        Parameters:
        -----------
        base : float
            Base value
        value : float
            Current value
        increment : float
            Increment value
            
        Returns:
        --------
        float
            Nearest cardinal angle value
        """
        # Calculate steps from base
        steps = round((value - base) / increment)
        
        # Calculate the value
        return base + (steps * increment)
    
    @staticmethod
    def get_nearest_ordinal_angle_value(base, value, increment):
        """
        Get the nearest ordinal angle value based on increment
        
        Parameters:
        -----------
        base : float
            Base value
        value : float
            Current value
        increment : float
            Increment value
            
        Returns:
        --------
        float
            Nearest ordinal angle value
        """
        # Ordinal angles use a different multiplier
        base_mult = 1.125
        
        # Calculate steps from base
        steps = round((value - base) / (increment * base_mult))
        
        # Calculate the value
        return base + (steps * increment * base_mult)
    
    @staticmethod
    def calculate_percentage_difference(price1, price2):
        """
        Calculate percentage difference between two prices
        
        Parameters:
        -----------
        price1 : float
            First price
        price2 : float
            Second price
            
        Returns:
        --------
        float
            Percentage difference
        """
        if price1 == 0:
            return float('inf') if price2 > 0 else -float('inf')
        
        return ((price2 - price1) / price1) * 100
    
    @staticmethod
    def calculate_gann_rotation(price, angle):
        """
        Calculate Gann rotation for a given price and angle
        
        Parameters:
        -----------
        price : float
            Price value
        angle : float
            Angle in degrees
            
        Returns:
        --------
        float
            Rotation value
        """
        # Convert angle to radians
        angle_rad = math.radians(angle)
        
        # Calculate square root of price
        sqrt_price = math.sqrt(price)
        
        # Calculate floor and fractional part
        floor_sqrt = math.floor(sqrt_price)
        frac_part = sqrt_price - floor_sqrt
        
        # Calculate rotation
        rotation = frac_part * 360
        
        # Adjust for angle
        adjusted_rotation = (rotation + angle) % 360
        
        return adjusted_rotation
    
    @staticmethod
    def is_fibonacci_level(price1, price2, tolerance=0.01):
        """
        Check if the ratio between two prices is near a Fibonacci level
        
        Parameters:
        -----------
        price1 : float
            First price
        price2 : float
            Second price
        tolerance : float
            Tolerance for comparing ratios
            
        Returns:
        --------
        tuple
            (bool, str) - (Is Fibonacci level, Level name)
        """
        # Common Fibonacci ratios
        fib_levels = {
            0.236: "23.6%",
            0.382: "38.2%",
            0.500: "50.0%",
            0.618: "61.8%",
            0.786: "78.6%",
            1.000: "100.0%",
            1.272: "127.2%",
            1.414: "141.4%",
            1.618: "161.8%",
            2.000: "200.0%",
            2.618: "261.8%"
        }
        
        if price1 == 0:
            return (False, "")
        
        # Calculate ratio
        ratio = abs(price2 / price1)
        
        # Check against Fibonacci levels
        for level, name in fib_levels.items():
            if abs(ratio - level) <= tolerance:
                return (True, name)
        
        return (False, "")
    
    @staticmethod
    def find_gann_square_root_relationships(price_levels):
        """
        Find square root relationships between price levels
        
        Parameters:
        -----------
        price_levels : list
            List of price levels
            
        Returns:
        --------
        list
            List of related price pairs
        """
        relationships = []
        
        for i, price1 in enumerate(price_levels):
            for j, price2 in enumerate(price_levels):
                if i >= j:
                    continue
                
                # Check if one is approximately the square of the other
                sqrt1 = math.sqrt(price1)
                sqrt2 = math.sqrt(price2)
                
                if abs(sqrt1 - price2) / price2 < 0.01:
                    relationships.append((price1, price2, "sqrt"))
                elif abs(sqrt2 - price1) / price1 < 0.01:
                    relationships.append((price2, price1, "sqrt"))
        
        return relationships