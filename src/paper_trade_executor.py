# -*- coding: utf-8 -*-
"""
Created on Fri Mar 14 00:30:33 2025

@author: mahes
"""

# src/paper_trade_executor.py

import logging
import json
import requests
from datetime import datetime
import os
from pathlib import Path
from src.symbol_registry import SymbolRegistry

class StrategyTemplate:
    """
    Represents a strategy template for paper trading
    """
    
    def __init__(self, template_id, name, parameters=None):
        """
        Initialize a strategy template
        
        Parameters:
        -----------
        template_id : str
            Unique identifier for the template
        name : str
            Name of the strategy template
        parameters : dict
            Strategy parameters
        """
        self.id = template_id
        self.name = name
        self.parameters = parameters or {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        
    def to_json(self):
        """
        Convert template to JSON
        
        Returns:
        --------
        str
            JSON representation of the template
        """
        return json.dumps({
            'id': self.id,
            'name': self.name,
            'parameters': self.parameters,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }, indent=2)
    
    @classmethod
    def from_json(cls, json_str):
        """
        Create template from JSON
        
        Parameters:
        -----------
        json_str : str
            JSON string
            
        Returns:
        --------
        StrategyTemplate
            Template object
        """
        data = json.loads(json_str)
        template = cls(data['id'], data['name'], data['parameters'])
        template.created_at = data['created_at']
        template.updated_at = data['updated_at']
        return template


class PaperTradeExecutor:
    """
    Paper trading executor using AlgoMojo webhooks
    """
    
    def __init__(self, api_config, trading_config, config_dir="config"):
        """
        Initialize the paper trade executor
        
        Parameters:
        -----------
        api_config : dict
            Dictionary containing API credentials
        trading_config : dict
            Dictionary containing trading parameters
        config_dir : str
            Directory containing configuration files
        """
        self.logger = logging.getLogger(__name__)
        
        # API configuration
        self.api_key = api_config.get('api_key')
        self.api_secret = api_config.get('api_secret')
        self.broker_code = api_config.get('broker_code')
        
        # Trading configuration
        self.strategy_name = trading_config.get('strategy_name', 'Gann Square of 9')
        self.webhook_url = trading_config.get('webhook_url', '')
        
        # Initialize symbol registry
        self.symbol_registry = SymbolRegistry(config_dir)
        
        # Template storage directory
        self.templates_dir = Path(trading_config.get('templates_dir', 'strategy_templates'))
        if not self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Load strategy templates
        self.templates = self.load_strategy_templates()
        
        # Track paper trades
        self.paper_trades = {}
        self.positions = {}
        
        self.logger.info("Paper Trade Executor initialized")
    
    def load_strategy_templates(self):
        """
        Load strategy templates from files
        
        Returns:
        --------
        dict
            Dictionary of strategy templates
        """
        templates = {}
        
        try:
            template_files = list(self.templates_dir.glob('*.json'))
            
            for file_path in template_files:
                with open(file_path, 'r') as f:
                    try:
                        template = StrategyTemplate.from_json(f.read())
                        templates[template.id] = template
                        self.logger.debug(f"Loaded template: {template.name} ({template.id})")
                    except Exception as e:
                        self.logger.error(f"Error loading template {file_path}: {e}")
            
            self.logger.info(f"Loaded {len(templates)} strategy templates")
            return templates
            
        except Exception as e:
            self.logger.error(f"Error loading strategy templates: {e}")
            return {}
    
    def create_strategy_template(self, name, parameters=None):
        """
        Create a new strategy template
        
        Parameters:
        -----------
        name : str
            Template name
        parameters : dict
            Strategy parameters
            
        Returns:
        --------
        StrategyTemplate
            The created template
        """
        # Generate a unique ID
        template_id = f"{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create template
        template = StrategyTemplate(template_id, name, parameters)
        
        # Save to dictionary
        self.templates[template_id] = template
        
        # Save to file
        file_path = self.templates_dir / f"{template_id}.json"
        with open(file_path, 'w') as f:
            f.write(template.to_json())
        
        self.logger.info(f"Created strategy template: {name} ({template_id})")
        return template
    
    def send_webhook_order(self, strategy_id, action, parameters=None):
        """
        Send an order via webhook
        
        Parameters:
        -----------
        strategy_id : str
            Strategy ID for the webhook
        action : str
            Trading action (BUY, SELL)
        parameters : dict
            Additional parameters (optional)
            
        Returns:
        --------
        dict
            Response data
        """
        if not self.webhook_url:
            self.logger.error("Webhook URL not configured")
            return {
                "status": "error",
                "message": "Webhook URL not configured"
            }
        
        # Ensure URL is properly formatted
        webhook_url = self.webhook_url
        if "PlaceStrategyOrder" not in webhook_url:
            webhook_url = f"{webhook_url.rstrip('/')}/PlaceStrategyOrder"
        
        # Create payload
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "date": timestamp,
            "action": action
        }
        
        # Add additional parameters
        if parameters:
            # Ensure symbol is in AlgoMojo format
            if 'symbol' in parameters:
                symbol = parameters['symbol']
                algomojo_symbol = self.symbol_registry.map_symbol(symbol, "tv", "algomojo")
                if algomojo_symbol != symbol:
                    self.logger.debug(f"Converted symbol for AlgoMojo: {symbol} -> {algomojo_symbol}")
                    parameters['symbol'] = algomojo_symbol
            
            payload.update(parameters)
        
        # Set headers
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            # Log the request
            self.logger.info(f"Sending webhook request: {webhook_url} - {json.dumps(payload)}")
            
            # Send the request
            response = requests.post(webhook_url, json=payload, headers=headers)
            
            # Process response
            if response.status_code == 200:
                response_data = response.json()
                
                # Generate order ID
                order_id = f"PAPER_{timestamp.replace(' ', '_')}_{strategy_id}"
                
                # Track the order
                self.paper_trades[order_id] = {
                    "strategy_id": strategy_id,
                    "action": action,
                    "parameters": parameters,
                    "timestamp": timestamp,
                    "response": response_data,
                    "status": "SUCCESS" if response_data.get("status") == "success" else "FAILED"
                }
                
                # Simulate execution
                self.simulate_execution(order_id)
                
                return {
                    "status": "success",
                    "order_id": order_id,
                    "response": response_data
                }
            else:
                self.logger.error(f"Webhook request failed: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Webhook request failed with status {response.status_code}",
                    "response": response.text
                }
                
        except Exception as e:
            self.logger.error(f"Error sending webhook request: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def simulate_execution(self, order_id):
        """
        Simulate the execution of a paper trade
        
        Parameters:
        -----------
        order_id : str
            Order ID to simulate
            
        Returns:
        --------
        dict
            Execution details
        """
        if order_id not in self.paper_trades:
            self.logger.error(f"Order not found: {order_id}")
            return None
        
        order = self.paper_trades[order_id]
        
        # Update status
        order["execution_time"] = datetime.now().isoformat()
        order["execution_status"] = "COMPLETED"
        
        # Extract parameters
        action = order.get("action")
        parameters = order.get("parameters", {})
        
        symbol = parameters.get("symbol")
        quantity = parameters.get("quantity", 1)
        price = parameters.get("price", 0)
        
        # If no price provided, use a simulated price
        if not price and symbol:
            # In a real implementation, this would fetch the current market price
            price = 1000.0  # Simulated price
        
        # Create a position record
        position_id = f"POS_{order_id}"
        position = {
            "order_id": order_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "entry_price": price,
            "entry_time": order["execution_time"],
            "status": "OPEN"
        }
        
        # Add to positions
        self.positions[position_id] = position
        
        self.logger.info(f"Simulated execution for order {order_id}: {symbol} {action} {quantity} @ {price}")
        
        return position
    
    def place_order(self, symbol, action, quantity, price_type="MARKET", price=0, product=None, exchange=None):
        """
        Place a paper trade order
        
        Parameters:
        -----------
        symbol : str
            Symbol to trade
        action : str
            "BUY" or "SELL"
        quantity : int
            Order quantity
        price_type : str
            "MARKET" or "LIMIT"
        price : float
            Limit price (if price_type is "LIMIT")
        product : str
            Product type (MIS, NRML, etc.)
        exchange : str
            Exchange identifier
            
        Returns:
        --------
        dict
            Order result
        """
        # Convert symbol to AlgoMojo format
        algomojo_symbol = self.symbol_registry.map_symbol(symbol, "tv", "algomojo")
        
        # Log the conversion
        if algomojo_symbol != symbol:
            self.logger.debug(f"Converted symbol for order: {symbol} -> {algomojo_symbol}")
        
        # Prepare parameters
        parameters = {
            "symbol": algomojo_symbol,
            "quantity": quantity,
            "price_type": price_type
        }
        
        if price_type == "LIMIT" and price > 0:
            parameters["price"] = price
        
        if product:
            parameters["product"] = product
        
        if exchange:
            parameters["exchange"] = exchange
        
        # Send webhook order
        return self.send_webhook_order("TRADE", action, parameters)
    
    def place_option_order(self, underlying, expiry_date, strike_price, option_type, action, quantity, 
                          price_type="MARKET", price=0, product=None, exchange=None):
        """
        Place a paper trade option order
        
        Parameters:
        -----------
        underlying : str
            Underlying symbol
        expiry_date : str
            Option expiry date
        strike_price : float
            Strike price
        option_type : str
            "CE" or "PE"
        action : str
            "BUY" or "SELL"
        quantity : int
            Order quantity
        price_type : str
            "MARKET" or "LIMIT"
        price : float
            Limit price (if price_type is "LIMIT")
        product : str
            Product type (MIS, NRML, etc.)
        exchange : str
            Exchange identifier
            
        Returns:
        --------
        dict
            Order result
        """
        # Convert underlying to AlgoMojo format
        underlying_algomojo = self.symbol_registry.map_symbol(underlying, "tv", "algomojo")
        
        # Construct option symbol
        option_symbol = f"{underlying_algomojo}-{expiry_date}-{int(strike_price)}-{option_type}"
        
        # Set exchange if not provided
        if not exchange:
            if underlying in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
                exchange = "NFO"
            elif underlying in ["CRUDEOIL", "GOLD", "SILVER"]:
                exchange = "MCX"
            else:
                exchange = "NFO"
        
        # Set product if not provided
        if not product:
            product = "NRML"
        
        # Place the order
        return self.place_order(
            symbol=option_symbol,
            action=action,
            quantity=quantity,
            price_type=price_type,
            price=price,
            product=product,
            exchange=exchange
        )
    
    def _place_option_order(self, symbol_info, option_type, price, quantity=None):
        """
        Helper method to place an option order based on symbol info
        
        Parameters:
        -----------
        symbol_info : dict
            Symbol information
        option_type : str
            "CE" or "PE"
        price : float
            Current price of the underlying
        quantity : int
            Order quantity (optional, if None uses lot size)
            
        Returns:
        --------
        dict
            Order result
        """
        symbol = symbol_info.get("symbol")
        symbol_type = symbol_info.get("type", "equity")
        lot_size = symbol_info.get("option_lot_size", 50)
        
        # Get expiry
        if symbol_type == "commodity":
            expiry = self.symbol_registry.get_commodity_expiry(symbol)
        else:
            expiry = self.symbol_registry.get_expiry_date(symbol_type)
        
        # Get strike price
        strike_price = self.symbol_registry.get_nearest_strike(symbol, price, round_up=(option_type=="PE"))
        
        # Set quantity if not provided
        if quantity is None:
            quantity = lot_size
        
        # Determine exchange
        if symbol_type == "index":
            exchange = "NFO"
        elif symbol_type == "commodity":
            exchange = "MCX"
        else:
            exchange = "NFO"
        
        # Place the option order
        return self.place_option_order(
            underlying=symbol,
            expiry_date=expiry,
            strike_price=strike_price,
            option_type=option_type,
            action="BUY",
            quantity=quantity,
            exchange=exchange
        )
    
    def get_order_status(self, order_id):
        """
        Get the status of a paper trade order
        
        Parameters:
        -----------
        order_id : str
            Order ID
            
        Returns:
        --------
        dict
            Order status
        """
        if order_id not in self.paper_trades:
            return {
                "status": "error",
                "message": "Order not found"
            }
        
        order = self.paper_trades[order_id]
        
        return {
            "status": "success",
            "data": order
        }
    
    def modify_order(self, order_id, parameters):
        """
        Modify a paper trade order
        
        Parameters:
        -----------
        order_id : str
            Order ID
        parameters : dict
            New parameters
            
        Returns:
        --------
        dict
            Result of the modification
        """
        if order_id not in self.paper_trades:
            return {
                "status": "error",
                "message": "Order not found"
            }
        
        order = self.paper_trades[order_id]
        
        # Update parameters
        if "parameters" in order:
            order["parameters"].update(parameters)
        
        order["modified_at"] = datetime.now().isoformat()
        
        self.logger.info(f"Modified paper trade order: {order_id}")
        
        return {
            "status": "success",
            "data": order
        }
    
    def cancel_order(self, order_id):
        """
        Cancel a paper trade order
        
        Parameters:
        -----------
        order_id : str
            Order ID
            
        Returns:
        --------
        dict
            Result of the cancellation
        """
        if order_id not in self.paper_trades:
            return {
                "status": "error",
                "message": "Order not found"
            }
        
        order = self.paper_trades[order_id]
        
        # Update status
        order["status"] = "CANCELLED"
        order["cancelled_at"] = datetime.now().isoformat()
        
        self.logger.info(f"Cancelled paper trade order: {order_id}")
        
        return {
            "status": "success",
            "data": order
        }
    
    def close_position(self, position_id, exit_price=None, exit_reason="MANUAL"):
        """
        Close a paper trade position
        
        Parameters:
        -----------
        position_id : str
            Position ID
        exit_price : float
            Exit price (optional)
        exit_reason : str
            Reason for exit
            
        Returns:
        --------
        dict
            Result of the position closure
        """
        if position_id not in self.positions:
            return {
                "status": "error",
                "message": "Position not found"
            }
        
        position = self.positions[position_id]
        
        # Skip if already closed
        if position["status"] == "CLOSED":
            return {
                "status": "error",
                "message": "Position already closed"
            }
        
        # Use provided exit price or simulate one
        if exit_price is None:
            # In a real implementation, this would fetch the current market price
            exit_price = position["entry_price"] * 1.01  # Simulated exit price
        
        # Calculate P&L
        if position["action"] == "BUY":
            pnl = (exit_price - position["entry_price"]) * position["quantity"]
        else:  # SELL
            pnl = (position["entry_price"] - exit_price) * position["quantity"]
        
        # Update position
        position["exit_price"] = exit_price
        position["exit_time"] = datetime.now().isoformat()
        position["exit_reason"] = exit_reason
        position["pnl"] = pnl
        position["status"] = "CLOSED"
        
        self.logger.info(f"Closed paper trade position: {position_id}, Exit: {exit_price}, P&L: {pnl}")
        
        return {
            "status": "success",
            "data": position
        }
    
    def close_all_positions(self, exit_reason="SYSTEM"):
        """
        Close all open paper trade positions
        
        Parameters:
        -----------
        exit_reason : str
            Reason for exit
            
        Returns:
        --------
        dict
            Results of the position closures
        """
        results = {}
        
        for position_id, position in self.positions.items():
            if position["status"] == "OPEN":
                result = self.close_position(position_id, None, exit_reason)
                results[position_id] = result
        
        self.logger.info(f"Closed all paper trade positions: {len(results)} positions")
        
        return {
            "status": "success",
            "data": results
        }
    
    def get_position_status(self, position_id):
        """
        Get the status of a paper trade position
        
        Parameters:
        -----------
        position_id : str
            Position ID
            
        Returns:
        --------
        dict
            Position status
        """
        if position_id not in self.positions:
            return {
                "status": "error",
                "message": "Position not found"
            }
        
        position = self.positions[position_id]
        
        return {
            "status": "success",
            "data": position
        }
    
    def get_all_positions(self, status=None):
        """
        Get all paper trade positions
        
        Parameters:
        -----------
        status : str
            Filter by status (optional)
            
        Returns:
        --------
        dict
            All positions
        """
        if status:
            filtered_positions = {pid: pos for pid, pos in self.positions.items() 
                                if pos["status"] == status}
            return {
                "status": "success",
                "data": filtered_positions
            }
        else:
            return {
                "status": "success",
                "data": self.positions
            }
    
    def get_positions_by_symbol(self, symbol):
        """
        Get all positions for a specific symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol to filter by
            
        Returns:
        --------
        dict
            Positions for the symbol
        """
        # Normalize symbol format
        algomojo_symbol = self.symbol_registry.map_symbol(symbol, "tv", "algomojo")
        
        filtered_positions = {pid: pos for pid, pos in self.positions.items() 
                            if pos["symbol"] == algomojo_symbol}
        
        return {
            "status": "success",
            "data": filtered_positions
        }
    
    def save_positions(self, filename="positions.json"):
        """
        Save positions to a file
        
        Parameters:
        -----------
        filename : str
            Output filename
            
        Returns:
        --------
        bool
            Success status
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.positions, f, indent=2)
            
            self.logger.info(f"Saved positions to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving positions: {e}")
            return False
    
    def load_positions(self, filename="positions.json"):
        """
        Load positions from a file
        
        Parameters:
        -----------
        filename : str
            Input filename
            
        Returns:
        --------
        bool
            Success status
        """
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    self.positions = json.load(f)
                
                self.logger.info(f"Loaded {len(self.positions)} positions from {filename}")
                return True
            else:
                self.logger.warning(f"Positions file not found: {filename}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading positions: {e}")
            return False