# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 23:28:33 2025

@author: mahes
"""

# -*- coding: utf-8 -*-
"""
AlgoMojo API Connector

This module provides a wrapper around the AlgoMojo REST API
for trade execution and account management.
"""

import requests
import json
import time
import logging
from typing import Dict, List, Union, Any, Optional
from datetime import datetime, timedelta

class AlgoMojoAPI:
    """
    AlgoMojo API client for executing trades and managing account
    """
    
    def __init__(self, api_key: str, api_secret: str, broker_code: str, base_url: str):
        """
        Initialize the AlgoMojo API client
        
        Parameters:
        -----------
        api_key : str
            API key for authentication
        api_secret : str
            API secret for authentication
        broker_code : str
            Broker code (e.g., 'ab' for Alice Blue)
        base_url : str
            Base URL for the AlgoMojo API
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.broker_code = broker_code
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        
        # Add authentication headers to session
        self.session.headers.update({
            'x-api-key': self.api_key,
            'x-api-secret': self.api_secret,
            'Content-Type': 'application/json'
        })
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """
        Test connection to the AlgoMojo API
        
        Returns:
        --------
        bool
            True if connection is successful, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/ping")
            
            if response.status_code == 200:
                self.logger.info("Successfully connected to AlgoMojo API")
                return True
            else:
                self.logger.error(f"Failed to connect to AlgoMojo API: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Exception connecting to AlgoMojo API: {str(e)}")
            return False
    
    def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile information
        
        Returns:
        --------
        dict
            User profile data
        """
        try:
            response = self.session.get(f"{self.base_url}/{self.broker_code}/profile")
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get profile: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            self.logger.error(f"Exception getting profile: {str(e)}")
            return {}
    
    def get_funds(self) -> Dict[str, Any]:
        """
        Get account funds information
        
        Returns:
        --------
        dict
            Account funds data
        """
        try:
            response = self.session.get(f"{self.base_url}/{self.broker_code}/funds")
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get funds: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            self.logger.error(f"Exception getting funds: {str(e)}")
            return {}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions
        
        Returns:
        --------
        list
            List of position dictionaries
        """
        try:
            response = self.session.get(f"{self.base_url}/{self.broker_code}/positions")
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get positions: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"Exception getting positions: {str(e)}")
            return []
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Get all orders
        
        Returns:
        --------
        list
            List of order dictionaries
        """
        try:
            response = self.session.get(f"{self.base_url}/{self.broker_code}/orders")
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get orders: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"Exception getting orders: {str(e)}")
            return []
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get status of a specific order
        
        Parameters:
        -----------
        order_id : str
            Order ID to check
            
        Returns:
        --------
        dict
            Order status information
        """
        try:
            response = self.session.get(f"{self.base_url}/{self.broker_code}/orderbook/{order_id}")
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get order status: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            self.logger.error(f"Exception getting order status: {str(e)}")
            return {}
    
    def place_order(self, 
                    symbol: str, 
                    action: str, 
                    quantity: int, 
                    price_type: str = 'MARKET',
                    price: float = 0.0,
                    trigger_price: float = 0.0,
                    exchange: str = 'NSE',
                    product: str = 'MIS') -> Dict[str, Any]:
        """
        Place a new order
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        action : str
            BUY or SELL
        quantity : int
            Order quantity
        price_type : str
            Order type (MARKET, LIMIT, SL, SL-M)
        price : float
            Order price for LIMIT orders
        trigger_price : float
            Trigger price for SL and SL-M orders
        exchange : str
            Exchange (NSE, BSE, NFO, MCX)
        product : str
            Product type (MIS, CNC, NRML)
            
        Returns:
        --------
        dict
            Order response
        """
        payload = {
            "trading_symbol": symbol,
            "exchange": exchange,
            "transaction_type": action,
            "quantity": quantity,
            "order_type": price_type,
            "product": product,
            "price": price if price > 0 else 0,
            "trigger_price": trigger_price if trigger_price > 0 else 0
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/{self.broker_code}/orders",
                data=json.dumps(payload)
            )
            
            if response.status_code in [200, 201]:
                self.logger.info(f"Order placed successfully: {symbol} {action} {quantity}")
                return {
                    "status": "success",
                    "order_id": response.json().get("order_id", ""),
                    "message": response.json().get("message", "Order placed")
                }
            else:
                self.logger.error(f"Failed to place order: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": response.text
                }
        except Exception as e:
            self.logger.error(f"Exception placing order: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def place_option_order(self,
                          underlying: str,
                          expiry_date: str,
                          strike_price: float,
                          option_type: str,
                          action: str,
                          quantity: int,
                          price_type: str = 'MARKET',
                          price: float = 0.0,
                          exchange: str = 'NFO',
                          product: str = 'MIS') -> Dict[str, Any]:
        """
        Place an options order
        
        Parameters:
        -----------
        underlying : str
            Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY')
        expiry_date : str
            Expiry date in format 'DDMMMYYYY' (e.g., '30MAR2023')
        strike_price : float
            Strike price
        option_type : str
            'CE' for Call, 'PE' for Put
        action : str
            'BUY' or 'SELL'
        quantity : int
            Order quantity
        price_type : str
            Order type (MARKET, LIMIT, SL, SL-M)
        price : float
            Order price for LIMIT orders
        exchange : str
            Exchange (NFO, MCX)
        product : str
            Product type (MIS, NRML)
            
        Returns:
        --------
        dict
            Order response
        """
        # Construct option symbol
        option_symbol = f"{underlying}-{expiry_date}-{strike_price}-{option_type}"
        
        return self.place_order(
            symbol=option_symbol,
            action=action,
            quantity=quantity,
            price_type=price_type,
            price=price,
            exchange=exchange,
            product=product
        )
    
    def modify_order(self,
                    order_id: str,
                    price: Optional[float] = None,
                    trigger_price: Optional[float] = None,
                    quantity: Optional[int] = None) -> Dict[str, Any]:
        """
        Modify an existing order
        
        Parameters:
        -----------
        order_id : str
            Order ID to modify
        price : float, optional
            New price
        trigger_price : float, optional
            New trigger price
        quantity : int, optional
            New quantity
            
        Returns:
        --------
        dict
            Modification response
        """
        payload = {
            "order_id": order_id
        }
        
        if price is not None:
            payload["price"] = price
        
        if trigger_price is not None:
            payload["trigger_price"] = trigger_price
        
        if quantity is not None:
            payload["quantity"] = quantity
        
        try:
            response = self.session.put(
                f"{self.base_url}/{self.broker_code}/orders/{order_id}",
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                self.logger.info(f"Order {order_id} modified successfully")
                return {
                    "status": "success",
                    "order_id": order_id,
                    "message": "Order modified"
                }
            else:
                self.logger.error(f"Failed to modify order: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": response.text
                }
        except Exception as e:
            self.logger.error(f"Exception modifying order: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an existing order
        
        Parameters:
        -----------
        order_id : str
            Order ID to cancel
            
        Returns:
        --------
        dict
            Cancellation response
        """
        try:
            response = self.session.delete(
                f"{self.base_url}/{self.broker_code}/orders/{order_id}"
            )
            
            if response.status_code == 200:
                self.logger.info(f"Order {order_id} cancelled successfully")
                return {
                    "status": "success",
                    "order_id": order_id,
                    "message": "Order cancelled"
                }
            else:
                self.logger.error(f"Failed to cancel order: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": response.text
                }
        except Exception as e:
            self.logger.error(f"Exception cancelling order: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_option_chain(self, 
                         underlying: str, 
                         expiry_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get option chain for an underlying
        
        Parameters:
        -----------
        underlying : str
            Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY')
        expiry_date : str, optional
            Expiry date in format 'DDMMMYYYY' (e.g., '30MAR2023')
            If None, uses the nearest expiry
            
        Returns:
        --------
        list
            List of option contracts
        """
        try:
            url = f"{self.base_url}/{self.broker_code}/option_chain?symbol={underlying}"
            
            if expiry_date:
                url += f"&expiry={expiry_date}"
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get option chain: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"Exception getting option chain: {str(e)}")
            return []
    
    def close_all_positions(self) -> Dict[str, Any]:
        """
        Close all open positions
        
        Returns:
        --------
        dict
            Response with summary of closed positions
        """
        positions = self.get_positions()
        
        if not positions:
            return {
                "status": "success",
                "message": "No positions to close",
                "closed": 0
            }
        
        closed_count = 0
        errors = []
        
        for position in positions:
            if position.get("quantity", 0) == 0:
                continue  # Skip positions with zero quantity
            
            symbol = position.get("trading_symbol")
            exchange = position.get("exchange")
            quantity = abs(position.get("quantity", 0))
            
            # Determine action (opposite of current position)
            action = "SELL" if position.get("quantity", 0) > 0 else "BUY"
            
            result = self.place_order(
                symbol=symbol,
                action=action,
                quantity=quantity,
                price_type="MARKET",
                exchange=exchange
            )
            
            if result.get("status") == "success":
                closed_count += 1
            else:
                errors.append({
                    "symbol": symbol,
                    "error": result.get("message")
                })
        
        return {
            "status": "success" if len(errors) == 0 else "partial",
            "message": f"Closed {closed_count} out of {len(positions)} positions",
            "closed": closed_count,
            "errors": errors
        }
    
    def get_historical_data(self,
                           symbol: str,
                           interval: str,
                           from_date: str,
                           to_date: str,
                           exchange: str = 'NSE') -> List[Dict[str, Any]]:
        """
        Get historical data for a symbol
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        interval : str
            Time interval (1m, 5m, 15m, 30m, 1h, 1d)
        from_date : str
            Start date in format 'YYYY-MM-DD'
        to_date : str
            End date in format 'YYYY-MM-DD'
        exchange : str
            Exchange (NSE, BSE, NFO, MCX)
            
        Returns:
        --------
        list
            List of candle data
        """
        try:
            url = f"{self.base_url}/{self.broker_code}/historical_data"
            
            payload = {
                "symbol": symbol,
                "exchange": exchange,
                "interval": interval,
                "from_date": from_date,
                "to_date": to_date
            }
            
            response = self.session.post(
                url,
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get historical data: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"Exception getting historical data: {str(e)}")
            return []