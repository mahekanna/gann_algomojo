# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 21:23:10 2025

@author: mahes
"""

# src/trade_executor.py

import logging
import time
from datetime import datetime
from algomojo.pyapi import api

class TradeExecutor:
    """
    Handles trade execution through the AlgoMojo API
    """
    
    def __init__(self, api_config, trading_config):
        """
        Initialize the trade executor with API and trading configuration
        
        Parameters:
        -----------
        api_config : dict
            Dictionary containing API credentials
            - api_key: AlgoMojo API key
            - api_secret: AlgoMojo API secret
            - broker_code: Broker code
            
        trading_config : dict
            Dictionary containing trading parameters
            - default_product: MIS or NRML
            - default_exchange: NSE, NFO, etc.
            - order_retry_count: Number of retries for failed orders
            - order_retry_delay: Delay between retries in seconds
        """
        self.logger = logging.getLogger(__name__)
        
        # API configuration
        self.api_key = api_config['api_key']
        self.api_secret = api_config['api_secret']
        self.broker_code = api_config['broker_code']
        
        # Trading configuration
        self.default_product = trading_config.get('default_product', 'MIS')
        self.default_exchange = trading_config.get('default_exchange', 'NSE')
        self.retry_count = trading_config.get('order_retry_count', 3)
        self.retry_delay = trading_config.get('order_retry_delay', 2)
        self.strategy_name = trading_config.get('strategy_name', 'Gann Square of 9')
        
        # Paper trading mode
        self.paper_trading = trading_config.get('paper_trading', True)
        self.webhook_url = trading_config.get('webhook_url', '')
        
        # Initialize API connection
        try:
            self.logger.info("Initializing AlgoMojo API connection")
            self.algomojo = api(api_key=self.api_key, api_secret=self.api_secret)
            self.logger.info("AlgoMojo API connection established")
        except Exception as e:
            self.logger.error(f"Failed to initialize AlgoMojo API: {e}")
            raise
        
        # Track open positions
        self.open_positions = {}
        
    def place_order(self, symbol, action, quantity, price_type="MARKET", price=0, 
                  product=None, exchange=None, option_details=None):
        """
        Place an order through the AlgoMojo API
        
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
            Exchange identifier (NSE, NFO, etc.)
        option_details : dict
            Optional details for options trading
            
        Returns:
        --------
        dict
            API response
        """
        if product is None:
            product = self.default_product
            
        if exchange is None:
            exchange = self.default_exchange
        
        # Determine if this is an options order
        is_options_order = option_details is not None or '-' in symbol and ('CE' in symbol or 'PE' in symbol)
        
        # Create an order ID for tracking
        order_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{symbol}_{action}"
        
        # Log order details
        self.logger.info(f"Placing order: {symbol} {action} {quantity} {price_type} {product}")
        
        # If paper trading is enabled, use webhook method
        if self.paper_trading:
            return self._place_paper_trade(symbol, action, quantity, price_type)
    
    # src/trade_executor.py (continued)

    def _place_paper_trade(self, symbol, action, quantity, price_type, price=0, product=None, exchange=None):
        """
        Place a paper trade using the webhook method for simulation
        
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
            Exchange identifier (NSE, NFO, etc.)
            
        Returns:
        --------
        dict
            Simulated API response
        """
        import requests
        import json
        from datetime import datetime
        
        try:
            # Current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create payload for webhook
            payload = {
                "date": timestamp,
                "action": action,
                "symbol": symbol,
                "quantity": quantity,
                "price_type": price_type,
                "price": price,
                "product": product or self.default_product,
                "exchange": exchange or self.default_exchange
            }
            
            # Set headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Send webhook request
            self.logger.info(f"Sending paper trade webhook: {json.dumps(payload)}")
            
            if self.webhook_url:
                response = requests.post(self.webhook_url, json=payload, headers=headers)
                
                # Check response
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Generate order ID
                    order_id = f"PAPER_{timestamp.replace(' ', '_')}_{symbol}"
                    
                    # Track the position
                    self._track_position(order_id, symbol, action, quantity, price or self.get_current_price(symbol))
                    
                    self.logger.info(f"Paper trade placed successfully: {order_id}")
                    
                    return {
                        "status": "success",
                        "data": {
                            "orderid": order_id,
                            "message": "Paper trade executed"
                        }
                    }
                else:
                    self.logger.error(f"Paper trade webhook failed: {response.status_code} - {response.text}")
                    return {
                        "status": "error",
                        "message": f"Webhook failed with status {response.status_code}"
                    }
            else:
                # No webhook URL, simulate locally
                order_id = f"PAPER_{timestamp.replace(' ', '_')}_{symbol}"
                
                # Track the position
                current_price = self.get_current_price(symbol)
                self._track_position(order_id, symbol, action, quantity, current_price)
                
                self.logger.info(f"Paper trade simulated locally: {order_id} at price {current_price}")
                
                return {
                    "status": "success",
                    "data": {
                        "orderid": order_id,
                        "message": "Paper trade simulated locally"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error in paper trade execution: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _place_real_order(self, symbol, action, quantity, price_type, price=0, product=None, exchange=None):
        """
        Place a real order through the AlgoMojo API
        
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
            Exchange identifier (NSE, NFO, etc.)
            
        Returns:
        --------
        dict
            API response
        """
        if product is None:
            product = self.default_product
            
        if exchange is None:
            exchange = self.default_exchange
        
        # Retry logic for order placement
        for attempt in range(self.retry_count):
            try:
                # Place the order using AlgoMojo API
                response = self.algomojo.PlaceOrder(
                    broker=self.broker_code,
                    strategy=self.strategy_name,
                    exchange=exchange,
                    symbol=symbol,
                    action=action,
                    product=product,
                    quantity=quantity,
                    pricetype=price_type,
                    price=price if price_type == "LIMIT" else 0
                )
                
                # Check if order was successful
                if response and 'data' in response and 'orderid' in response['data']:
                    order_id = response['data']['orderid']
                    self.logger.info(f"Order placed successfully: {order_id}")
                    
                    # Track the position if it's a success
                    self._track_position(order_id, symbol, action, quantity, price or self.get_current_price(symbol))
                    
                    return response
                else:
                    self.logger.warning(f"Order response format unexpected: {response}")
                    # Wait before retry
                    time.sleep(self.retry_delay)
            except Exception as e:
                self.logger.error(f"Order attempt {attempt+1} failed: {e}")
                # Wait before retry
                time.sleep(self.retry_delay)
        
        # If we get here, all attempts failed
        self.logger.error(f"Failed to place order after {self.retry_count} attempts")
        return {
            "status": "error",
            "message": f"Failed to place order after {self.retry_count} attempts"
        }
    
    def _track_position(self, order_id, symbol, action, quantity, price):
        """
        Track an open position for paper trading or position management
        
        Parameters:
        -----------
        order_id : str
            Order ID
        symbol : str
            Trading symbol
        action : str
            "BUY" or "SELL"
        quantity : int
            Order quantity
        price : float
            Execution price
        """
        position = {
            "order_id": order_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "timestamp": datetime.now().isoformat(),
            "status": "OPEN"
        }
        
        self.open_positions[order_id] = position
        self.logger.info(f"Tracking position: {position}")
    
    def place_options_order(self, underlying, expiry_date, strike_price, option_type, 
                           action, quantity, price_type="MARKET", price=0):
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
            
        Returns:
        --------
        dict
            API response
        """
        try:
            self.logger.info(f"Placing options order: {underlying} {expiry_date} {strike_price} {option_type}")
            
            if self.paper_trading:
                # For paper trading, construct a symbol and use regular order placement
                symbol = f"{underlying}{expiry_date}{strike_price}{option_type}"
                return self._place_paper_trade(
                    symbol=symbol,
                    action=action,
                    quantity=quantity,
                    price_type=price_type,
                    price=price,
                    product="NRML",
                    exchange="NFO"
                )
            else:
                # Use the AlgoMojo's options order function
                response = self.algomojo.PlaceFOOptionsOrder(
                    broker=self.broker_code,
                    strategy=self.strategy_name,
                    spot_symbol=underlying,
                    expiry_date=expiry_date,
                    action=action,
                    product="NRML",
                    pricetype=price_type,
                    quantity=str(quantity),
                    price=str(price) if price_type == "LIMIT" else "0",
                    option_type=option_type,
                    strike_int=str(int(strike_price)),
                    offset="0",
                    splitorder="NO",
                    split_quantity=str(quantity)
                )
                
                # Track the position if successful
                if response and 'data' in response and 'orderid' in response['data']:
                    order_id = response['data']['orderid']
                    symbol = f"{underlying}{expiry_date}{strike_price}{option_type}"
                    self._track_position(order_id, symbol, action, quantity, price or self.get_option_price(underlying, strike_price, option_type))
                
                return response
                
        except Exception as e:
            self.logger.error(f"Failed to place options order: {e}")
            return {
                "status": "error",
                "message": str(e)
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
        if self.paper_trading:
            # For paper trading, just update our local tracking
            if order_id in self.open_positions:
                position = self.open_positions[order_id]
                
                if price is not None:
                    position["price"] = price
                    
                if quantity is not None:
                    position["quantity"] = quantity
                
                self.logger.info(f"Paper trade order modified: {order_id}")
                return {
                    "status": "success",
                    "message": "Paper trade order modified"
                }
            else:
                self.logger.warning(f"Order ID not found for modification: {order_id}")
                return {
                    "status": "error",
                    "message": "Order ID not found"
                }
        else:
            # Get the order details first
            order_details = self.get_order_status(order_id)
            
            if not order_details or "data" not in order_details:
                self.logger.error(f"Could not retrieve order details for modification: {order_id}")
                return {
                    "status": "error",
                    "message": "Could not retrieve order details"
                }
            
            # Extract required fields from order_details
            order_data = order_details["data"]
            symbol = order_data.get("symbol")
            action = order_data.get("action")
            product = order_data.get("product")
            exchange = order_data.get("exchange")
            price_type = order_data.get("pricetype")
            
            # Use provided values or defaults from original order
            new_price = price if price is not None else order_data.get("price", 0)
            new_quantity = quantity if quantity is not None else order_data.get("quantity")
            new_trigger_price = trigger_price if trigger_price is not None else order_data.get("trigger_price", 0)
            
            try:
                response = self.algomojo.ModifyOrder(
                    broker=self.broker_code,
                    exchange=exchange,
                    symbol=symbol,
                    order_id=order_id,
                    action=action,
                    product=product,
                    pricetype=price_type,
                    price=str(new_price),
                    quantity=str(new_quantity),
                    disclosed_quantity="0",
                    trigger_price=str(new_trigger_price)
                )
                
                return response
            except Exception as e:
                self.logger.error(f"Failed to modify order {order_id}: {e}")
                return {
                    "status": "error",
                    "message": str(e)
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
        
        if self.paper_trading:
            # For paper trading, just update our local tracking
            if order_id in self.open_positions:
                self.open_positions[order_id]["status"] = "CANCELLED"
                self.logger.info(f"Paper trade order cancelled: {order_id}")
                return {
                    "status": "success",
                    "message": "Paper trade order cancelled"
                }
            else:
                self.logger.warning(f"Order ID not found for cancellation: {order_id}")
                return {
                    "status": "error",
                    "message": "Order ID not found"
                }
        else:
            try:
                response = self.algomojo.CancelOrder(
                    broker=self.broker_code,
                    order_id=order_id
                )
                
                return response
            except Exception as e:
                self.logger.error(f"Failed to cancel order {order_id}: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }
    
    def close_position(self, symbol, product="MIS"):
        """
        Close a position for a specific symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol to close position for
        product : str
            Product type (MIS, NRML)
            
        Returns:
        --------
        dict
            API response
        """
        self.logger.info(f"Closing position for {symbol} ({product})")
        
        if self.paper_trading:
            # For paper trading, find all positions for this symbol and mark as closed
            closed_positions = []
            
            for order_id, position in self.open_positions.items():
                if position["symbol"] == symbol and position["status"] == "OPEN":
                    position["status"] = "CLOSED"
                    closed_positions.append(order_id)
            
            self.logger.info(f"Closed paper positions for {symbol}: {closed_positions}")
            return {
                "status": "success",
                "message": f"Closed {len(closed_positions)} paper positions",
                "closed_positions": closed_positions
            }
        else:
            try:
                response = self.algomojo.SquareOffPosition(
                    broker=self.broker_code,
                    exchange=self.default_exchange,
                    product=product,
                    symbol=symbol
                )
                
                return response
            except Exception as e:
                self.logger.error(f"Failed to close position for {symbol}: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }
    
    def close_all_positions(self):
        """
        Close all open positions
        
        Returns:
        --------
        dict
            API response
        """
        self.logger.info("Closing all positions")
        
        if self.paper_trading:
            # For paper trading, mark all open positions as closed
            closed_count = 0
            
            for position in self.open_positions.values():
                if position["status"] == "OPEN":
                    position["status"] = "CLOSED"
                    closed_count += 1
            
            self.logger.info(f"Closed {closed_count} paper positions")
            return {
                "status": "success",
                "message": f"Closed {closed_count} paper positions"
            }
        else:
            try:
                response = self.algomojo.SquareOffAllPosition(
                    broker=self.broker_code
                )
                
                return response
            except Exception as e:
                self.logger.error(f"Failed to close all positions: {e}")
                return {
                    "status": "error",
                    "message": str(e)
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
        if self.paper_trading:
            # For paper trading, return from our local tracking
            if order_id in self.open_positions:
                position = self.open_positions[order_id]
                return {
                    "status": "success",
                    "data": {
                        "orderid": order_id,
                        "symbol": position["symbol"],
                        "status": position["status"],
                        "price": position["price"],
                        "quantity": position["quantity"],
                        "action": position["action"],
                        "timestamp": position["timestamp"]
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "Order ID not found"
                }
        else:
            try:
                response = self.algomojo.OrderStatus(
                    broker=self.broker_code,
                    order_id=order_id
                )
                
                return response
            except Exception as e:
                self.logger.error(f"Failed to get status for order {order_id}: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }
    
    def get_position_book(self):
        """
        Get current positions
        
        Returns:
        --------
        dict
            Position book information
        """
        if self.paper_trading:
            # For paper trading, create position book from our local tracking
            positions = []
            
            for position in self.open_positions.values():
                if position["status"] == "OPEN":
                    positions.append({
                        "symbol": position["symbol"],
                        "quantity": position["quantity"],
                        "average_price": position["price"],
                        "pnl": 0,  # Would need current price to calculate
                        "product": self.default_product
                    })
            
            return {
                "status": "success",
                "data": positions
            }
        else:
            try:
                response = self.algomojo.PositionBook(
                    broker=self.broker_code
                )
                
                return response
            except Exception as e:
                self.logger.error(f"Failed to get position book: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }
    
    def get_current_price(self, symbol, exchange=None):
        """
        Get the current market price for a symbol
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange (defaults to self.default_exchange)
            
        Returns:
        --------
        float
            Current market price
        """
        if exchange is None:
            exchange = self.default_exchange
        
        try:
            response = self.algomojo.GetQuote(
                broker=self.broker_code,
                exchange=exchange,
                symbol=symbol
            )
            
            if response and "data" in response:
                # Extract the last price from response
                last_price = response["data"].get("last_price")
                if last_price:
                    return float(last_price)
            
            self.logger.warning(f"Could not get current price for {symbol}, using fallback")
            return 0  # Fallback value
            
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {e}")
            return 0  # Fallback value
    
    def get_account_info(self):
        """
        Get account information including funds
        
        Returns:
        --------
        dict
            Account information
        """
        if self.paper_trading:
            # For paper trading, return simulated account info
            return {
                "status": "success",
                "data": {
                    "balance": 1000000,  # Simulated balance
                    "used_margin": 0,
                    "available_margin": 1000000,
                    "is_paper_trading": True
                }
            }
        else:
            try:
                response = self.algomojo.Funds(
                    broker=self.broker_code
                )
                
                return response
            except Exception as e:
                self.logger.error(f"Failed to get account info: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }
    
    def get_option_price(self, underlying, strike_price, option_type):
        """
        Get current price for an option
        
        Parameters:
        -----------
        underlying : str
            Underlying symbol
        strike_price : float
            Strike price
        option_type : str
            "CE" or "PE"
            
        Returns:
        --------
        float
            Current option price
        """
        # This is a simplified implementation
        # In a real system, you would need to determine the
        # actual option symbol format based on exchange rules
        
        # Try to construct an option symbol
        # Format may vary by broker/exchange
        symbol = f"{underlying}-{strike_price}{option_type}"
        
        # Get the current price
        price = self.get_current_price(symbol, "NFO")
        
        # If price is 0, it might be because the symbol format is wrong
        # You might need to implement option chain lookup
        
        return price