# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 23:09:03 2025

@author: mahes
"""

# -*- coding: utf-8 -*-
"""
Gann Square of 9 Trading System - Web Dashboard
This module provides a web interface for the Gann Square of 9 Trading System
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Import custom modules
from src.tvdata_handler import TVDataHandler
from src.gann_calculator import GannCalculator
from src.symbol_registry import SymbolRegistry
from src.risk_manager import RiskManager
from src.logger import setup_logger, TradeLogger
from src.paper_trade_executor import PaperTradeExecutor
from src.live_trade_executor import LiveTradeExecutor

# Setup logging
logger = setup_logger()

# Initialize Flask app
app = Flask(__name__, 
            static_folder="web/static", 
            template_folder="web/templates")

# Global state variables
config_dir = "config"
trading_system = None
system_status = {
    "running": False,
    "mode": "paper",
    "last_update": datetime.now().isoformat(),
    "signals": [],
    "positions": {},
    "performance": {
        "win_rate": 0,
        "profit_factor": 0,
        "total_trades": 0,
        "pnl": 0
    }
}

# Load configurations
def load_configurations(config_path=config_dir):
    """Load configuration files"""
    configs = {}
    
    try:
        # Load API configuration
        api_config_path = os.path.join(config_path, "api_config.json")
        with open(api_config_path, 'r') as f:
            configs["api_config"] = json.load(f)
        
        # Load trading configuration
        trading_config_path = os.path.join(config_path, "trading_config.json")
        with open(trading_config_path, 'r') as f:
            configs["trading_config"] = json.load(f)
        
        # Load symbols configuration
        symbols_config_path = os.path.join(config_path, "symbols.json")
        with open(symbols_config_path, 'r') as f:
            configs["symbols_config"] = json.load(f)
        
        logger.info("All configurations loaded successfully")
        return configs
        
    except Exception as e:
        logger.error(f"Error loading configurations: {e}")
        return None

# Initialize components
def initialize_components(configs, mode="paper"):
    """Initialize system components"""
    components = {}
    
    try:
        # Initialize symbol registry
        components["symbol_registry"] = SymbolRegistry(config_dir)
        
        # Initialize data handler
        components["data_handler"] = TVDataHandler(config_dir)
        
        # Initialize Gann calculator
        gann_params = configs["trading_config"].get('gann_parameters', {})
        components["gann_calculator"] = GannCalculator(gann_params)
        
        # Initialize trade executor based on mode
        if mode == "paper":
            components["trade_executor"] = PaperTradeExecutor(
                configs["api_config"], 
                configs["trading_config"],
                config_dir
            )
            logger.info("Using PaperTradeExecutor for paper trading")
        else:
            components["trade_executor"] = LiveTradeExecutor(
                configs["api_config"], 
                configs["trading_config"]
            )
            logger.info("Using LiveTradeExecutor for live trading")
        
        # Initialize risk manager
        risk_params = configs["trading_config"].get('risk_parameters', {})
        components["risk_manager"] = RiskManager(risk_params)
        
        logger.info("All components initialized successfully")
        return components
        
    except Exception as e:
        logger.error(f"Error initializing components: {e}")
        return None

# Initialize Trading System
def init_trading_system(mode="paper"):
    """Initialize or reinitialize the trading system"""
    global trading_system, system_status
    
    # Load configurations
    configs = load_configurations()
    if not configs:
        return False
    
    # Initialize components
    components = initialize_components(configs, mode)
    if not components:
        return False
    
    # Update system status
    system_status["mode"] = mode
    system_status["last_update"] = datetime.now().isoformat()
    
    # Create trading system object
    trading_system = {
        "configs": configs,
        "components": components,
        "status": system_status
    }
    
    return True

# Background thread to update system status
def status_updater():
    """Background thread to update system status"""
    global trading_system, system_status
    
    while system_status["running"]:
        try:
            if trading_system:
                # Get current positions
                if "components" in trading_system and "risk_manager" in trading_system["components"]:
                    risk_manager = trading_system["components"]["risk_manager"]
                    system_status["positions"] = risk_manager.get_active_positions()
                    
                    # Get performance metrics
                    stats = risk_manager.get_trade_statistics()
                    system_status["performance"] = {
                        "win_rate": stats.get("win_rate", 0) * 100,  # Convert to percentage
                        "profit_factor": stats.get("profit_factor", 0),
                        "total_trades": stats.get("total_trades", 0),
                        "pnl": stats.get("net_profit", 0)
                    }
                
                # Update timestamp
                system_status["last_update"] = datetime.now().isoformat()
            
            # Sleep for 5 seconds before next update
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error in status updater: {e}")
            time.sleep(10)  # Longer sleep on error

# Routes
@app.route('/')
def index():
    """Dashboard home page"""
    return render_template('index.html', 
                          status=system_status,
                          mode=system_status["mode"])

@app.route('/dashboard')
def dashboard():
    """Main dashboard view"""
    return render_template('dashboard.html', 
                          status=system_status,
                          mode=system_status["mode"])

@app.route('/symbols')
def symbols():
    """Symbols management page"""
    symbols_data = []
    
    if trading_system and "components" in trading_system and "symbol_registry" in trading_system["components"]:
        symbol_registry = trading_system["components"]["symbol_registry"]
        symbols_data = symbol_registry.get_all_symbols()
    
    return render_template('symbols.html', 
                          symbols=symbols_data,
                          status=system_status)

@app.route('/signals')
def signals():
    """Trading signals page"""
    return render_template('signals.html', 
                          signals=system_status["signals"],
                          status=system_status)

@app.route('/positions')
def positions():
    """Positions management page"""
    return render_template('positions.html', 
                          positions=system_status["positions"],
                          status=system_status)

@app.route('/configuration')
def configuration():
    """Configuration page"""
    configs = {}
    
    if trading_system and "configs" in trading_system:
        configs = trading_system["configs"]
    
    return render_template('configuration.html', 
                          configs=configs,
                          status=system_status)

@app.route('/logs')
def logs():
    """Log viewer page"""
    # Get the latest log entries
    log_entries = []
    log_file = Path("logs") / f"gann_trading_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    if log_file.exists():
        with open(log_file, 'r') as f:
            # Get the last 100 lines
            lines = f.readlines()[-100:]
            log_entries = [line.strip() for line in lines]
    
    return render_template('logs.html', 
                          log_entries=log_entries,
                          status=system_status)

# API routes for AJAX requests
@app.route('/api/status')
def api_status():
    """Get current system status"""
    return jsonify(system_status)

@app.route('/api/start', methods=['POST'])
def api_start():
    """Start the trading system"""
    global system_status
    
    # Check if already running
    if system_status["running"]:
        return jsonify({"status": "error", "message": "System is already running"})
    
    # Get mode from request
    data = request.json
    mode = data.get("mode", "paper")
    
    # Initialize or reinitialize trading system
    if not trading_system or trading_system["status"]["mode"] != mode:
        if not init_trading_system(mode):
            return jsonify({"status": "error", "message": "Failed to initialize trading system"})
    
    # Start background threads
    system_status["running"] = True
    
    # Start status updater thread
    status_thread = threading.Thread(target=status_updater, daemon=True)
    status_thread.start()
    
    return jsonify({"status": "success", "message": f"System started in {mode} mode"})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Stop the trading system"""
    global system_status
    
    # Check if already stopped
    if not system_status["running"]:
        return jsonify({"status": "error", "message": "System is not running"})
    
    # Get request data
    data = request.json
    close_positions = data.get("close_positions", False)
    
    # Close positions if requested
    if close_positions and trading_system and "components" in trading_system and "trade_executor" in trading_system["components"]:
        try:
            trade_executor = trading_system["components"]["trade_executor"]
            result = trade_executor.close_all_positions()
            logger.info(f"Closed all positions: {result}")
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
    
    # Stop background threads
    system_status["running"] = False
    
    return jsonify({"status": "success", "message": "System stopped"})

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    """Calculate Gann levels for a given price"""
    data = request.json
    price = data.get("price")
    
    if not price:
        return jsonify({"status": "error", "message": "Price is required"})
    
    try:
        price = float(price)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid price format"})
    
    # Calculate Gann levels
    if trading_system and "components" in trading_system and "gann_calculator" in trading_system["components"]:
        gann_calculator = trading_system["components"]["gann_calculator"]
        results = gann_calculator.calculate(price)
        
        if results:
            return jsonify({"status": "success", "data": results})
        else:
            return jsonify({"status": "error", "message": "Failed to calculate Gann levels"})
    else:
        return jsonify({"status": "error", "message": "Gann calculator not initialized"})

@app.route('/api/market_data/<symbol>')
def api_market_data(symbol):
    """Get market data for a symbol"""
    if not trading_system or "components" not in trading_system or "data_handler" not in trading_system["components"]:
        return jsonify({"status": "error", "message": "Data handler not initialized"})
    
    data_handler = trading_system["components"]["data_handler"]
    
    # Get the exchange from query parameter or use default
    exchange = request.args.get("exchange", "NSE")
    
    # Get current price
    current_price = data_handler.get_current_price(symbol, exchange)
    
    if current_price is None:
        return jsonify({"status": "error", "message": f"Could not get price for {symbol}"})
    
    # Get previous candle
    timeframe = request.args.get("timeframe", "1h")
    prev_candle = data_handler.get_previous_candle(symbol, exchange, timeframe)
    
    return jsonify({
        "status": "success",
        "data": {
            "symbol": symbol,
            "exchange": exchange,
            "current_price": current_price,
            "previous_candle": prev_candle,
            "timestamp": datetime.now().isoformat()
        }
    })

@app.route('/api/place_order', methods=['POST'])
def api_place_order():
    """Place a manual order"""
    if not system_status["running"]:
        return jsonify({"status": "error", "message": "Trading system is not running"})
    
    if not trading_system or "components" not in trading_system or "trade_executor" not in trading_system["components"]:
        return jsonify({"status": "error", "message": "Trade executor not initialized"})
    
    # Get order details from request
    data = request.json
    symbol = data.get("symbol")
    action = data.get("action")
    quantity = data.get("quantity")
    price_type = data.get("price_type", "MARKET")
    price = data.get("price", 0)
    
    # Validate required fields
    if not symbol or not action or not quantity:
        return jsonify({"status": "error", "message": "Symbol, action, and quantity are required"})
    
    # Convert quantity to integer
    try:
        quantity = int(quantity)
    except ValueError:
        return jsonify({"status": "error", "message": "Quantity must be a number"})
    
    # Place the order
    trade_executor = trading_system["components"]["trade_executor"]
    result = trade_executor.place_order(
        symbol=symbol,
        action=action,
        quantity=quantity,
        price_type=price_type,
        price=float(price) if price else 0
    )
    
    return jsonify({"status": "success", "data": result})

@app.route('/api/close_position/<position_id>', methods=['POST'])
def api_close_position(position_id):
    """Close a specific position"""
    if not system_status["running"]:
        return jsonify({"status": "error", "message": "Trading system is not running"})
    
    if not trading_system or "components" not in trading_system:
        return jsonify({"status": "error", "message": "Trading system not initialized"})
    
    if "risk_manager" not in trading_system["components"] or "trade_executor" not in trading_system["components"]:
        return jsonify({"status": "error", "message": "Required components not initialized"})
    
    risk_manager = trading_system["components"]["risk_manager"]
    trade_executor = trading_system["components"]["trade_executor"]
    
    # Get position details
    position = risk_manager.get_position_status(position_id)
    
    if not position:
        return jsonify({"status": "error", "message": f"Position {position_id} not found"})
    
    # Get current price
    symbol = position.get("symbol")
    
    if not symbol:
        return jsonify({"status": "error", "message": "Invalid position data"})
    
    # Get symbol info
    symbol_registry = trading_system["components"]["symbol_registry"]
    symbol_info = symbol_registry.get_symbol_info(symbol)
    
    if not symbol_info:
        return jsonify({"status": "error", "message": f"Symbol info not found for {symbol}"})
    
    # Get current price
    data_handler = trading_system["components"]["data_handler"]
    exchange = symbol_info.get("exchange", "NSE")
    current_price = data_handler.get_current_price(symbol, exchange)
    
    if not current_price:
        return jsonify({"status": "error", "message": f"Could not get price for {symbol}"})
    
    # Close position in risk manager
    closed_position = risk_manager.close_position(position_id, current_price, "Manual close from dashboard")
    
    if not closed_position:
        return jsonify({"status": "error", "message": "Failed to close position in risk manager"})
    
    # Execute the exit in the market
    if position.get("action") == "BUY":
        # For long equity position, sell
        result = trade_executor.place_order(
            symbol=symbol,
            action="SELL",
            quantity=position.get("quantity", 0),
            price_type="MARKET",
            exchange=exchange
        )
    else:
        # For options, we can just sell the option
        result = trade_executor.place_order(
            symbol=symbol,
            action="SELL",
            quantity=position.get("quantity", 0),
            price_type="MARKET",
            exchange="NFO" if symbol_info.get("type") in ["equity", "index"] else "MCX"
        )
    
    return jsonify({"status": "success", "data": result})

def create_app():
    """Create the Flask app instance"""
    return app

if __name__ == "__main__":
    # Initialize the trading system
    init_trading_system()
    
    # Run the Flask app
    app.run(debug=True, host="0.0.0.0", port=5000)