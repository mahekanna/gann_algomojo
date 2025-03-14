# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 21:45:53 2025

@author: mahes
"""

# src/live_trade_executor.py

import logging
import time
from datetime import datetime
import json
from pathlib import Path

class RetryHandler:
    """
    Handles retry logic for API calls
    """
    
    def __init__(self, max_attempts=3, delay=2, backoff_factor=2):
        """
        Initialize the retry handler
        
        Parameters:
        -----------
        max_attempts : int
            Maximum number of retry attempts
        delay : int
            Initial delay between retries in seconds
        backoff_factor : float
            Factor to increase delay with each retry
        """
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.logger = logging.getLogger(__name__)
    
    def execute(self, func, *args, **kwargs):
        """
        Execute a function with retry logic
        
        Parameters:
        -----------
        func : callable
            Function to execute
        *args, **kwargs
            Arguments to pass to the function
            
        Returns:
        --------
        object
            Result of the function call
            
        Raises:
        -------
        Exception
            If all retry attempts fail
        """
        attempts = 0
        last_exception = None
        
        while attempts < self.max_attempts:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                last_exception = e
                
                if attempts < self.max_attempts:
                    wait_time = self.delay * (self.backoff_factor ** (attempts - 1))
                    self.logger.warning(f"Attempt {attempts} failed: {str(e)}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {self.max_attempts} attempts failed.")
        
        # If we get here, all attempts failed
        raise last_exception


class LiveTradeExecutor:
    """
    Handles live trade execution through the AlgoMojo API
    """
    
    def __init__(self, api_config, trading_config):
        """
        Initialize the live trade executor
        
        Parameters:
        -----------
        api_config : dict
            Dictionary containing API credentials
        trading_config : dict
            Dictionary containing trading parameters
        """
        self.logger = logging.getLogger(__name__)
        
        # API configuration
        self.api_key = api_config.get('api_key')
        self.api_secret = api_config.get('api_secret')
        self.broker_code = api_config.get('broker_code')
        
        # Trading configuration
        self.default_product = trading_config.get('default_product', 'MIS')
        self.default_exchange = trading_config.get('default_exchange', 'NSE')
        self.strategy_name = trading_config.get('strategy_name', 'Gann Square of 9')
        
        # Create retry handler
        retry_config = trading_config.get('retry_config', {})
        self.retry_handler = RetryHandler(
            max_attempts=retry_config.get('max_attempts', 3),
            delay=retry_config.get('delay', 2),
            backoff_factor=retry_config.get('backoff_factor', 2)
        )
        
        # Initialize API connection
        try:
            from algomojo.pyapi import api
            self.algomojo = api(api_key=self.api_key, api_secret=self.api_secret)
            self.logger.info("AlgoMojo API connection established for live trading")
        except Exception as e:
            self.logger.error(f"Failed to initialize AlgoMojo API: {e}")
            raise
        
        # Validate connection
        self.check_connection()
        
        # Track orders and positions
        self.orders = {}
        self.positions = {}
        
        # Create order tracking directory
        self.orders_dir = Path("orders")
        if not self.orders_dir.exists():
            self.orders_dir.mkdir(parents=True, exist_ok=True)
        
        # Load cached orders if available
        self._load_orders()
        
        self.logger.info("Live Trade Executor initialized")
    
    def check_connection(self):
        """
        Check API connection
        
        Returns:
        --------
        bool
            Connection status
        """
        try:
            # Test connection with a simple API call
            self.logger.info("Testing API connection...")
            profile = self.retry_handler.execute(
                self.algomojo.Profile,
                broker=self.broker_code
            )
            
            if profile and profile.get('status') == 'success':
                self.logger.info(f"API connection successful: {self.broker_code}")
                return True
            else:
                self.logger.error(f"API connection failed: {profile}")
                return False
                
        except Exception as e:
            self.logger.error(f"API connection check failed: {e}")
            return False
    
    def place_order(self, symbol, action, quantity, price_type="MARKET", price=0, 
                   product=None, exchange=None, order_tag=None):
        """
        Place a live order through AlgoMojo API
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        action : str
            "BUY" or "SELL"
        quantity : int
            Order quantity
        price_type : str
            "MARKET" or "LIMIT"
        price : float
            Price for limit orders
        product : str
            "MIS" or "NRML"
        exchange : str
            Exchange identifier
        order_tag : str
            Custom tag for the order
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Placing order: {symbol} {action} {quantity} {price_type}")
        
        # Use defaults if not provided
        if product is None:
            product = self.default_product
        
        if exchange is None:
            exchange = self.default_exchange
        
        # Validate parameters
        if not symbol or not action or not quantity:
            error_msg = f"Invalid order parameters: symbol={symbol}, action={action}, quantity={quantity}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        
        # Prepare order parameters
        order_params = {
            "broker": self.broker_code,
            "strategy": self.strategy_name,
            "exchange": exchange,
            "symbol": symbol,
            "action": action,
            "product": product,
            "quantity": quantity,
            "pricetype": price_type
        }
        
        # Add price for limit orders
        if price_type == "LIMIT" and price > 0:
            order_params["price"] = price
        
        try:
            # Place the order with retry logic
            self.logger.info(f"Sending order to AlgoMojo: {order_params}")
            response = self.retry_handler.execute(
                self.algomojo.PlaceOrder,
                **order_params
            )
            
            # Check response
            if response and response.get('status') == 'success' and 'data' in response:
                order_id = response['data'].get('orderid')
                
                if order_id:
                    # Track the order
                    timestamp = datetime.now().isoformat()
                    self.orders[order_id] = {
                        "params": order_params,
                        "response": response,
                        "status": "PLACED",
                        "placed_at": timestamp,
                        "tag": order_tag,
                        "updates": []
                    }
                    
                    # Save order to file
                    self._save_order(order_id)
                    
                    self.logger.info(f"Order placed successfully: {order_id}")
                    
                    # Start monitoring the order status
                    self._start_order_monitoring(order_id)
                    
                    return {
                        "status": "success",
                        "order_id": order_id,
                        "data": response['data']
                    }
                else:
                    error_msg = "Order ID not found in response"
                    self.logger.error(f"{error_msg}: {response}")
                    return {
                        "status": "error",
                        "message": error_msg,
                        "response": response
                    }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error placing order: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def place_options_order(self, underlying, expiry_date, strike_price, option_type, 
                           action, quantity, price_type="MARKET", price=0, product=None):
        """
        Place an options order
        
        Parameters:
        -----------
        underlying : str
            Underlying symbol (e.g., "NIFTY")
        expiry_date : str
            Expiry date (format as required by broker)
        strike_price : float
            Strike price
        option_type : str
            "CE" or "PE"
        action : str
            "BUY" or "SELL"
        quantity : int
            Number of contracts
        price_type : str
            "MARKET" or "LIMIT"
        price : float
            Price for limit orders
        product : str
            "MIS" or "NRML"
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Placing options order: {underlying} {expiry_date} {strike_price} {option_type}")
        
        # Use default product if not provided
        if product is None:
            product = self.default_product if self.default_product != "MIS" else "NRML"
        
        try:
            # Prepare order parameters
            order_params = {
                "broker": self.broker_code,
                "strategy": self.strategy_name,
                "spot_symbol": underlying,
                "expiry_date": expiry_date,
                "action": action,
                "product": product,
                "pricetype": price_type,
                "quantity": str(quantity),
                "price": str(price) if price_type == "LIMIT" else "0",
                "option_type": option_type,
                "strike_int": str(int(strike_price)),
                "offset": "0",
                "splitorder": "NO",
                "split_quantity": str(quantity)
            }
            
            # Place the order with retry logic
            self.logger.info(f"Sending options order to AlgoMojo: {order_params}")
            response = self.retry_handler.execute(
                self.algomojo.PlaceFOOptionsOrder,
                **order_params
            )
            
            # Check response
            if response and response.get('status') == 'success' and 'data' in response:
                order_id = response['data'].get('orderid')
                
                if order_id:
                    # Track the order
                    timestamp = datetime.now().isoformat()
                    self.orders[order_id] = {
                        "params": order_params,
                        "response": response,
                        "status": "PLACED",
                        "placed_at": timestamp,
                        "type": "OPTION",
                        "updates": []
                    }
                    
                    # Save order to file
                    self._save_order(order_id)
                    
                    self.logger.info(f"Options order placed successfully: {order_id}")
                    
                    # Start monitoring the order status
                    self._start_order_monitoring(order_id)
                    
                    return {
                        "status": "success",
                        "order_id": order_id,
                        "data": response['data']
                    }
                else:
                    error_msg = "Order ID not found in response"
                    self.logger.error(f"{error_msg}: {response}")
                    return {
                        "status": "error",
                        "message": error_msg,
                        "response": response
                    }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error placing options order: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def place_bracket_order(self, symbol, action, quantity, price_type, price, 
                           stop_loss, target, trailing_stop_loss=0, exchange=None):
        """
        Place a bracket order
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        action : str
            "BUY" or "SELL"
        quantity : int
            Order quantity
        price_type : str
            "MARKET" or "LIMIT"
        price : float
            Price for limit orders
        stop_loss : float
            Stop loss points
        target : float
            Target points
        trailing_stop_loss : float
            Trailing stop loss points
        exchange : str
            Exchange identifier
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Placing bracket order: {symbol} {action} {quantity} SL:{stop_loss} Target:{target}")
        
        if exchange is None:
            exchange = self.default_exchange
        
        try:
            # Prepare order parameters
            order_params = {
                "broker": self.broker_code,
                "strategy": self.strategy_name,
                "exchange": exchange,
                "symbol": symbol,
                "action": action,
                "pricetype": price_type,
                "quantity": str(quantity),
                "price": str(price),
                "squareoff": str(target),
                "stoploss": str(stop_loss),
                "trailing_stoploss": str(trailing_stop_loss),
                "trigger_price": "0",
                "disclosed_quantity": "0"
            }
            
            # Place the bracket order with retry logic
            self.logger.info(f"Sending bracket order to AlgoMojo: {order_params}")
            response = self.retry_handler.execute(
                self.algomojo.PlaceBOOrder,
                **order_params
            )
            
            # Check response
            if response and response.get('status') == 'success' and 'data' in response:
                order_id = response['data'].get('orderid')
                
                if order_id:
                    # Track the order
                    timestamp = datetime.now().isoformat()
                    self.orders[order_id] = {
                        "params": order_params,
                        "response": response,
                        "status": "PLACED",
                        "placed_at": timestamp,
                        "type": "BRACKET",
                        "updates": []
                    }
                    
                    # Save order to file
                    self._save_order(order_id)
                    
                    self.logger.info(f"Bracket order placed successfully: {order_id}")
                    
                    return {
                        "status": "success",
                        "order_id": order_id,
                        "data": response['data']
                    }
                else:
                    error_msg = "Order ID not found in response"
                    self.logger.error(f"{error_msg}: {response}")
                    return {
                        "status": "error",
                        "message": error_msg,
                        "response": response
                    }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error placing bracket order: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def place_cover_order(self, symbol, action, quantity, price_type, price, stop_price, exchange=None):
        """
        Place a cover order
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        action : str
            "BUY" or "SELL"
        quantity : int
            Order quantity
        price_type : str
            "MARKET" or "LIMIT"
        price : float
            Price for limit orders
        stop_price : float
            Stop loss price
        exchange : str
            Exchange identifier
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Placing cover order: {symbol} {action} {quantity} Stop:{stop_price}")
        
        if exchange is None:
            exchange = self.default_exchange
        
        try:
            # Prepare order parameters
            order_params = {
                "broker": self.broker_code,
                "strategy": self.strategy_name,
                "exchange": exchange,
                "symbol": symbol,
                "action": action,
                "pricetype": price_type,
                "quantity": str(quantity),
                "price": str(price),
                "stop_price": str(stop_price)
            }
            
            # Place the cover order with retry logic
            self.logger.info(f"Sending cover order to AlgoMojo: {order_params}")
            response = self.retry_handler.execute(
                self.algomojo.PlaceCOOrder,
                **order_params
            )
            
            # Check response
            if response and response.get('status') == 'success' and 'data' in response:
                order_id = response['data'].get('orderid')
                
                if order_id:
                    # Track the order
                    timestamp = datetime.now().isoformat()
                    self.orders[order_id] = {
                        "params": order_params,
                        "response": response,
                        "status": "PLACED",
                        "placed_at": timestamp,
                        "type": "COVER",
                        "updates": []
                    }
                    
                    # Save order to file
                    self._save_order(order_id)
                    
                    self.logger.info(f"Cover order placed successfully: {order_id}")
                    
                    return {
                        "status": "success",
                        "order_id": order_id,
                        "data": response['data']
                    }
                else:
                    error_msg = "Order ID not found in response"
                    self.logger.error(f"{error_msg}: {response}")
                    return {
                        "status": "error",
                        "message": error_msg,
                        "response": response
                    }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error placing cover order: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def modify_order(self, order_id, price=None, quantity=None, trigger_price=None):
        """
        Modify an existing order
        
        Parameters:
        -----------
        order_id : str
            Order ID to modify
        price : float
            New price (for limit orders)
        quantity : int
            New quantity
        trigger_price : float
            New trigger price (for stop orders)
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Modifying order: {order_id}")
        
        # Check if we have the order details
        if order_id not in self.orders:
            # Try to get order details from API
            order_details = self.get_order_status(order_id)
            
            if order_details and order_details.get('status') == 'success' and 'data' in order_details:
                # Store the details
                self.orders[order_id] = {
                    "params": {},
                    "response": order_details,
                    "status": order_details['data'].get('status', 'UNKNOWN'),
                    "placed_at": datetime.now().isoformat(),
                    "updates": []
                }
            else:
                error_msg = f"Order details not found for modification: {order_id}"
                self.logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg
                }
        
        try:
            # Get the order details
            order_data = self.orders[order_id]
            
            # Get original parameters
            original_params = order_data.get('params', {})
            
            # Get symbol and other details from original params or response
            if 'symbol' in original_params:
                symbol = original_params['symbol']
            elif 'data' in order_data.get('response', {}) and 'symbol' in order_data['response']['data']:
                symbol = order_data['response']['data']['symbol']
            else:
                # Get the details from API
                order_status = self.get_order_status(order_id)
                if order_status and 'data' in order_status and 'symbol' in order_status['data']:
                    symbol = order_status['data']['symbol']
                else:
                    error_msg = f"Symbol not found for order: {order_id}"
                    self.logger.error(error_msg)
                    return {
                        "status": "error",
                        "message": error_msg
                    }
            
            # Determine exchange, action, and product from original params or response
            exchange = original_params.get('exchange', self.default_exchange)
            
            if 'action' in original_params:
                action = original_params['action']
            elif 'data' in order_data.get('response', {}) and 'action' in order_data['response']['data']:
                action = order_data['response']['data']['action']
            else:
                # Default to BUY if unknown
                action = "BUY"
            
            if 'product' in original_params:
                product = original_params['product']
            elif 'data' in order_data.get('response', {}) and 'product' in order_data['response']['data']:
                product = order_data['response']['data']['product']
            else:
                # Default to MIS if unknown
                product = self.default_product
            
            # Determine price type
            price_type = original_params.get('pricetype', 'LIMIT' if price is not None else 'MARKET')
            
            # Use provided values or original values
            new_price = price if price is not None else original_params.get('price', 0)
            new_quantity = quantity if quantity is not None else original_params.get('quantity', 1)
            new_trigger_price = trigger_price if trigger_price is not None else original_params.get('trigger_price', 0)
            
            # Prepare modify parameters
            modify_params = {
                "broker": self.broker_code,
                "exchange": exchange,
                "symbol": symbol,
                "order_id": order_id,
                "action": action,
                "product": product,
                "pricetype": price_type,
                "price": str(new_price),
                "quantity": str(new_quantity),
                "disclosed_quantity": "0",
                "trigger_price": str(new_trigger_price)
            }
            
            # Modify the order with retry logic
            self.logger.info(f"Sending modify request to AlgoMojo: {modify_params}")
            response = self.retry_handler.execute(
                self.algomojo.ModifyOrder,
                **modify_params
            )
            
            # Check response
            if response and response.get('status') == 'success':
                # Update order tracking
                timestamp = datetime.now().isoformat()
                
                # Add to updates
                update = {
                    "timestamp": timestamp,
                    "type": "MODIFY",
                    "new_params": modify_params,
                    "response": response
                }
                
                order_data['updates'].append(update)
                order_data['status'] = "MODIFIED"
                
                # Save order to file
                self._save_order(order_id)
                
                self.logger.info(f"Order modified successfully: {order_id}")
                
                return {
                    "status": "success",
                    "data": response.get('data', {})
                }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error modifying order {order_id}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def cancel_order(self, order_id):
        """
        Cancel an order
        
        Parameters:
        -----------
        order_id : str
            Order ID to cancel
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Cancelling order: {order_id}")
        
        try:
            # Cancel the order with retry logic
            response = self.retry_handler.execute(
                self.algomojo.CancelOrder,
                broker=self.broker_code,
                order_id=order_id
            )
            
            # Check response
            if response and response.get('status') == 'success':
                # Update order tracking if available
                if order_id in self.orders:
                    timestamp = datetime.now().isoformat()
                    
                    # Add to updates
                    update = {
                        "timestamp": timestamp,
                        "type": "CANCEL",
                        "response": response
                    }
                    
                    self.orders[order_id]['updates'].append(update)
                    self.orders[order_id]['status'] = "CANCELLED"
                    
                    # Save order to file
                    self._save_order(order_id)
                
                self.logger.info(f"Order cancelled successfully: {order_id}")
                
                return {
                    "status": "success",
                    "data": response.get('data', {})
                }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error cancelling order {order_id}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def cancel_all_orders(self):
        """
        Cancel all open orders
        
        Returns:
        --------
        dict
            API response
        """
        self.logger.info("Cancelling all orders")
        
        try:
            # Cancel all orders with retry logic
            response = self.retry_handler.execute(
                self.algomojo.CancelAllOrder,
                broker=self.broker_code
            )
            
            # Check response
            if response and response.get('status') == 'success':
                # Update all tracked orders
                timestamp = datetime.now().isoformat()
                
                for order_id in self.orders:
                    if self.orders[order_id]['status'] not in ["COMPLETE", "CANCELLED", "REJECTED"]:
                        # Add to updates
                        update = {
                            "timestamp": timestamp,
                            "type": "CANCEL_ALL",
                            "response": response
                        }
                        
                        self.orders[order_id]['updates'].append(update)
                        self.orders[order_id]['status'] = "CANCELLED"
                        
                        # Save order to file
                        self._save_order(order_id)
                
                self.logger.info("All orders cancelled successfully")
                
                return {
                    "status": "success",
                    "data": response.get('data', {})
                }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error cancelling all orders: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_order_status(self, order_id):
        """
        Get the status of an order
        
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
            # Get order status with retry logic
            response = self.retry_handler.execute(
                self.algomojo.OrderStatus,
                broker=self.broker_code,
                order_id=order_id
            )
            
            # Check response
            if response and response.get('status') == 'success':
                # Update order tracking if available
                if order_id in self.orders:
                    # Add to updates if status changed
                    current_status = self.orders[order_id].get('status')
                    new_status = response.get('data', {}).get('status')
                    
                    if new_status and current_status != new_status:
                        timestamp = datetime.now().isoformat()
                        
                        update = {
                            "timestamp": timestamp,
                            "type": "STATUS_UPDATE",
                            "old_status": current_status,
                            "new_status": new_status,
                            "response": response
                        }
                        
                        self.orders[order_id]['updates'].append(update)
                        self.orders[order_id]['status'] = new_status
                        
                        # Save order to file
                        self._save_order(order_id)
                
                return response
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error getting status for order {order_id}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_order_history(self, order_id):
        """
        Get the history of an order
        
        Parameters:
        -----------
        order_id : str
            Order ID to check
            
        Returns:
        --------
        dict
            Order history information
        """
        try:
            # Get order history with retry logic
            response = self.retry_handler.execute(
                self.algomojo.OrderHistory,
                broker=self.broker_code,
                order_id=order_id
            )
            
            return response
                
        except Exception as e:
            error_msg = f"Error getting history for order {order_id}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_order_book(self):
        """
        Get the order book
        
        Returns:
        --------
        dict
            Order book information
        """
        try:
            # Get order book with retry logic
            response = self.retry_handler.execute(
                self.algomojo.OrderBook,
                broker=self.broker_code
            )
            
            # Update tracked orders with latest status
            if response and response.get('status') == 'success' and 'data' in response:
                orders_data = response['data']
                
                for order in orders_data:
                    if 'orderid' in order:
                        order_id = order['orderid']
                        
                        # Update in our tracking if exists
                        if order_id in self.orders:
                            current_status = self.orders[order_id].get('status')
                            new_status = order.get('status')
                            
                            if new_status and current_status != new_status:
                                timestamp = datetime.now().isoformat()
                                
                                update = {
                                    "timestamp": timestamp,
                                    "type": "STATUS_UPDATE",
                                    "old_status": current_status,
                                    "new_status": new_status,
                                    "data": order
                                }
                                
                                self.orders[order_id]['updates'].append(update)
                                self.orders[order_id]['status'] = new_status
                                
                                # Save order to file
                                self._save_order(order_id)
            
            return response
                
        except Exception as e:
            error_msg = f"Error getting order book: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_trade_book(self):
        """
        Get the trade book
        
        Returns:
        --------
        dict
            Trade book information
        """
        try:
            # Get trade book with retry logic
            response = self.retry_handler.execute(
                self.algomojo.TradeBook,
                broker=self.broker_code
            )
            
            return response
                
        except Exception as e:
            error_msg = f"Error getting trade book: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_position_book(self):
        """
        Get the position book
        
        Returns:
        --------
        dict
            Position book information
        """
        try:
            # Get position book with retry logic
            response = self.retry_handler.execute(
                self.algomojo.PositionBook,
                broker=self.broker_code
            )
            
            # Update positions dictionary with latest data
            if response and response.get('status') == 'success' and 'data' in response:
                positions_data = response['data']
                
                # Reset positions dictionary
                self.positions = {}
                
                # Update with latest positions
                for position in positions_data:
                    if 'symbol' in position:
                        symbol = position['symbol']
                        self.positions[symbol] = position
            
            return response
                
        except Exception as e:
            error_msg = f"Error getting position book: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_open_positions(self, symbol=None, product=None):
        """
        Get open positions for a symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol to check (optional)
        product : str
            Product type (optional)
            
        Returns:
        --------
        dict
            Open positions information
        """
        try:
            # Prepare parameters
            params = {
                "broker": self.broker_code
            }
            
            if symbol:
                params["symbol"] = symbol
            
            if product:
                params["product"] = product
            
            # Get open positions with retry logic
            response = self.retry_handler.execute(
                self.algomojo.OpenPositions,
                **params
            )
            
            return response
                
        except Exception as e:
            error_msg = f"Error getting open positions: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def square_off_position(self, symbol, product="MIS", exchange=None):
        """
        Square off a position
        
        Parameters:
        -----------
        symbol : str
            Symbol to square off
        product : str
            Product type
        exchange : str
            Exchange identifier
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Squaring off position: {symbol} ({product})")
        
        if exchange is None:
            exchange = self.default_exchange
        
        try:
            # Square off position with retry logic
            response = self.retry_handler.execute(
                self.algomojo.SquareOffPosition,
                broker=self.broker_code,
                exchange=exchange,
                product=product,
                symbol=symbol
            )
            
            # Check response
            if response and response.get('status') == 'success':
                self.logger.info(f"Position squared off successfully: {symbol}")
                
                # Update positions (if we're tracking this symbol)
                if symbol in self.positions:
                    self.positions[symbol]['is_open'] = False
                    self.positions[symbol]['squared_off_at'] = datetime.now().isoformat()
                
                return {
                    "status": "success",
                    "data": response.get('data', {})
                }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error squaring off position for {symbol}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def square_off_all_positions(self):
        """
        Square off all positions
        
        Returns:
        --------
        dict
            API response
        """
        self.logger.info("Squaring off all positions")
        
        try:
            # Square off all positions with retry logic
            response = self.retry_handler.execute(
                self.algomojo.SquareOffAllPosition,
                broker=self.broker_code
            )
            
            # Check response
            if response and response.get('status') == 'success':
                self.logger.info("All positions squared off successfully")
                
                # Update all positions as closed
                for symbol in self.positions:
                    self.positions[symbol]['is_open'] = False
                    self.positions[symbol]['squared_off_at'] = datetime.now().isoformat()
                
                return {
                    "status": "success",
                    "data": response.get('data', {})
                }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error squaring off all positions: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def exit_bracket_order(self, order_id):
        """
        Exit a bracket order
        
        Parameters:
        -----------
        order_id : str
            Order ID of the bracket order
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Exiting bracket order: {order_id}")
        
        try:
            # Exit bracket order with retry logic
            response = self.retry_handler.execute(
                self.algomojo.ExitBOOrder,
                broker=self.broker_code,
                order_id=order_id
            )
            
            # Check response
            if response and response.get('status') == 'success':
                # Update order tracking if available
                if order_id in self.orders:
                    timestamp = datetime.now().isoformat()
                    
                    # Add to updates
                    update = {
                        "timestamp": timestamp,
                        "type": "EXIT_BO",
                        "response": response
                    }
                    
                    self.orders[order_id]['updates'].append(update)
                    self.orders[order_id]['status'] = "EXITED"
                    
                    # Save order to file
                    self._save_order(order_id)
                
                self.logger.info(f"Bracket order exited successfully: {order_id}")
                
                return {
                    "status": "success",
                    "data": response.get('data', {})
                }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error exiting bracket order {order_id}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def exit_cover_order(self, order_id):
        """
        Exit a cover order
        
        Parameters:
        -----------
        order_id : str
            Order ID of the cover order
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Exiting cover order: {order_id}")
        
        try:
            # Exit cover order with retry logic
            response = self.retry_handler.execute(
                self.algomojo.ExitCOOrder,
                broker=self.broker_code,
                order_id=order_id
            )
            
            # Check response
            if response and response.get('status') == 'success':
                # Update order tracking if available
                if order_id in self.orders:
                    timestamp = datetime.now().isoformat()
                    
                    # Add to updates
                    update = {
                        "timestamp": timestamp,
                        "type": "EXIT_CO",
                        "response": response
                    }
                    
                    self.orders[order_id]['updates'].append(update)
                    self.orders[order_id]['status'] = "EXITED"
                    
                    # Save order to file
                    self._save_order(order_id)
                
                self.logger.info(f"Cover order exited successfully: {order_id}")
                
                return {
                    "status": "success",
                    "data": response.get('data', {})
                }
            else:
                error_msg = "Invalid response from API"
                self.logger.error(f"{error_msg}: {response}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "response": response
                }
                
        except Exception as e:
            error_msg = f"Error exiting cover order {order_id}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_funds(self):
        """
        Get account funds
        
        Returns:
        --------
        dict
            Funds information
        """
        try:
            # Get funds with retry logic
            response = self.retry_handler.execute(
                self.algomojo.Funds,
                broker=self.broker_code
            )
            
            return response
                
        except Exception as e:
            error_msg = f"Error getting funds: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_holdings(self):
        """
        Get account holdings
        
        Returns:
        --------
        dict
            Holdings information
        """
        try:
            # Get holdings with retry logic
            response = self.retry_handler.execute(
                self.algomojo.Holdings,
                broker=self.broker_code
            )
            
            return response
                
        except Exception as e:
            error_msg = f"Error getting holdings: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_quote(self, symbol, exchange=None):
        """
        Get market quote for a symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol to get quote for
        exchange : str
            Exchange identifier
            
        Returns:
        --------
        dict
            Quote information
        """
        if exchange is None:
            exchange = self.default_exchange
        
        try:
            # Get quote with retry logic
            response = self.retry_handler.execute(
                self.algomojo.GetQuote,
                broker=self.broker_code,
                exchange=exchange,
                symbol=symbol
            )
            
            return response
                
        except Exception as e:
            error_msg = f"Error getting quote for {symbol}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def get_profile(self):
        """
        Get broker profile
        
        Returns:
        --------
        dict
            Profile information
        """
        try:
            # Get profile with retry logic
            response = self.retry_handler.execute(
                self.algomojo.Profile,
                broker=self.broker_code
            )
            
            return response
                
        except Exception as e:
            error_msg = f"Error getting profile: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    def _start_order_monitoring(self, order_id):
        """
        Start monitoring an order asynchronously
        
        Parameters:
        -----------
        order_id : str
            Order ID to monitor
        """
        # Note: In a production system, you would use threads or an event loop
        # to monitor orders asynchronously. For simplicity, this is just a placeholder.
        self.logger.info(f"Started monitoring order: {order_id}")
        
        # In a real implementation, you would create a thread:
        # import threading
        # monitor_thread = threading.Thread(
        #     target=self._monitor_order,
        #     args=(order_id,),
        #     daemon=True
        # )
        # monitor_thread.start()
    
    def _monitor_order(self, order_id, check_interval=5, max_checks=12):
        """
        Monitor an order until it completes or fails
        
        Parameters:
        -----------
        order_id : str
            Order ID to monitor
        check_interval : int
            Interval between status checks in seconds
        max_checks : int
            Maximum number of status checks
        """
        checks = 0
        
        while checks < max_checks:
            # Get order status
            status_response = self.get_order_status(order_id)
            
            if status_response and status_response.get('status') == 'success':
                order_status = status_response.get('data', {}).get('status')
                
                # Check if order has reached a terminal state
                if order_status in ["COMPLETE", "REJECTED", "CANCELLED"]:
                    self.logger.info(f"Order {order_id} reached terminal state: {order_status}")
                    break
            
            # Wait for next check
            time.sleep(check_interval)
            checks += 1
        
        if checks >= max_checks:
            self.logger.warning(f"Order monitoring timed out for {order_id}")
    
    def _save_order(self, order_id):
        """
        Save order details to file
        
        Parameters:
        -----------
        order_id : str
            Order ID to save
        """
        try:
            if order_id in self.orders:
                file_path = self.orders_dir / f"{order_id}.json"
                
                with open(file_path, 'w') as f:
                    # Create a JSON-safe copy of the order data
                    order_data = self.orders[order_id].copy()
                    
                    # Clean up response data if needed
                    if 'response' in order_data and not isinstance(order_data['response'], dict):
                        order_data['response'] = {"data": str(order_data['response'])}
                    
                    json.dump(order_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving order {order_id} to file: {e}")
    
    def _load_orders(self):
        """
        Load cached orders from files
        """
        try:
            order_files = list(self.orders_dir.glob("*.json"))
            
            for file_path in order_files:
                try:
                    with open(file_path, 'r') as f:
                        order_data = json.load(f)
                        
                    order_id = file_path.stem
                    self.orders[order_id] = order_data
                    
                except Exception as e:
                    self.logger.error(f"Error loading order from {file_path}: {e}")
            
            self.logger.info(f"Loaded {len(self.orders)} cached orders")
            
        except Exception as e:
            self.logger.error(f"Error loading cached orders: {e}")
    
    def close_position(self, symbol, product="MIS", exchange=None, reason="Manual"):
        """
        Close a position (wrapper for square_off_position)
        
        Parameters:
        -----------
        symbol : str
            Symbol to close position for
        product : str
            Product type
        exchange : str
            Exchange identifier
        reason : str
            Reason for closing
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Closing position for {symbol} ({product}), reason: {reason}")
        
        response = self.square_off_position(symbol, product, exchange)
        
        if response and response.get('status') == 'success':
            # Log the closure reason
            if symbol in self.positions:
                self.positions[symbol]['close_reason'] = reason
            
            self.logger.info(f"Position closed successfully: {symbol}")
        
        return response
    
    def close_all_positions(self, reason="System"):
        """
        Close all positions (wrapper for square_off_all_positions)
        
        Parameters:
        -----------
        reason : str
            Reason for closing
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Closing all positions, reason: {reason}")
        
        response = self.square_off_all_positions()
        
        if response and response.get('status') == 'success':
            # Log the closure reason for all positions
            for symbol in self.positions:
                self.positions[symbol]['close_reason'] = reason
            
            self.logger.info("All positions closed successfully")
        
        return response
    
    def get_account_info(self):
        """
        Get comprehensive account information
        
        Returns:
        --------
        dict
            Account information including funds, positions, and orders
        """
        # Get funds
        funds_response = self.get_funds()
        
        # Get positions
        positions_response = self.get_position_book()
        
        # Get order book
        orders_response = self.get_order_book()
        
        # Compile account info
        account_info = {
            "funds": funds_response.get('data', {}) if funds_response and funds_response.get('status') == 'success' else {},
            "positions": positions_response.get('data', []) if positions_response and positions_response.get('status') == 'success' else [],
            "orders": orders_response.get('data', []) if orders_response and orders_response.get('status') == 'success' else [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate account balance if available
        if 'funds' in account_info and 'balance' in account_info['funds']:
            account_info['balance'] = account_info['funds']['balance']
        
        return account_info