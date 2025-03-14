# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 21:39:14 2025

@author: mahes
"""

# src/logger.py

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

def setup_logger():
    """
    Setup the logger for the Gann Trading System
    
    Returns:
    --------
    logger : logging.Logger
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Get the current date for log file
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(logs_dir, f'gann_trading_{current_date}.log')
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    
    # Create file handler with rotation
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=30  # Keep logs for 30 days
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Create a system logger
    logger = logging.getLogger('gann_trading')
    logger.info("Logger initialized")
    
    return logger

def get_logger(name):
    """
    Get a logger with the specified name
    
    Parameters:
    -----------
    name : str
        Logger name
        
    Returns:
    --------
    logger : logging.Logger
        Logger instance
    """
    return logging.getLogger(name)

class TradeLogger:
    """
    Specialized logger for trade-related events
    """
    
    def __init__(self, log_file=None):
        """
        Initialize the trade logger
        
        Parameters:
        -----------
        log_file : str
            Optional path to log file
        """
        self.logger = logging.getLogger('gann_trading.trades')
        
        # If a specific log file is requested
        if log_file:
            logs_dir = os.path.dirname(log_file)
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            # Create a special file handler just for trades
            trade_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=100  # Keep up to 100 files
            )
            
            formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(message)s')
            trade_handler.setFormatter(formatter)
            trade_handler.setLevel(logging.INFO)
            
            self.logger.addHandler(trade_handler)
    
    def log_signal(self, symbol, timeframe, signal_type, price, gann_level):
        """
        Log a trading signal
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        timeframe : str
            Timeframe of the signal
        signal_type : str
            Type of signal (BUY, SELL, etc.)
        price : float
            Current price
        gann_level : float
            Gann level that generated the signal
        """
        msg = f"SIGNAL|{symbol}|{timeframe}|{signal_type}|{price}|{gann_level}"
        self.logger.info(msg)
    
    def log_order(self, symbol, order_type, action, quantity, price, order_id=None):
        """
        Log an order
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        order_type : str
            Type of order (MARKET, LIMIT, etc.)
        action : str
            Order action (BUY, SELL)
        quantity : int
            Order quantity
        price : float
            Order price
        order_id : str
            Order ID (optional)
        """
        msg = f"ORDER|{symbol}|{order_type}|{action}|{quantity}|{price}"
        if order_id:
            msg += f"|{order_id}"
        
        self.logger.info(msg)
    
    def log_fill(self, symbol, action, quantity, price, order_id, fill_time=None):
        """
        Log an order fill
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        action : str
            Order action (BUY, SELL)
        quantity : int
            Filled quantity
        price : float
            Fill price
        order_id : str
            Order ID
        fill_time : str
            Fill time (optional)
        """
        if fill_time is None:
            fill_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        msg = f"FILL|{symbol}|{action}|{quantity}|{price}|{order_id}|{fill_time}"
        self.logger.info(msg)
    
    def log_cancel(self, symbol, order_id, reason=None):
        """
        Log an order cancellation
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        order_id : str
            Order ID
        reason : str
            Cancellation reason (optional)
        """
        msg = f"CANCEL|{symbol}|{order_id}"
        if reason:
            msg += f"|{reason}"
        
        self.logger.info(msg)
    
    def log_position(self, symbol, action, quantity, entry_price, exit_price=None, pnl=None, exit_reason=None):
        """
        Log a position update
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        action : str
            Position direction (LONG, SHORT)
        quantity : int
            Position size
        entry_price : float
            Entry price
        exit_price : float
            Exit price (optional)
        pnl : float
            Realized P&L (optional)
        exit_reason : str
            Exit reason (optional)
        """
        if exit_price is None:
            # Position open
            msg = f"POSITION_OPEN|{symbol}|{action}|{quantity}|{entry_price}"
        else:
            # Position close
            msg = f"POSITION_CLOSE|{symbol}|{action}|{quantity}|{entry_price}|{exit_price}"
            if pnl is not None:
                msg += f"|{pnl}"
            if exit_reason:
                msg += f"|{exit_reason}"
        
        self.logger.info(msg)
    
    def log_error(self, context, error_msg):
        """
        Log an error
        
        Parameters:
        -----------
        context : str
            Context of the error
        error_msg : str
            Error message
        """
        msg = f"ERROR|{context}|{error_msg}"
        self.logger.error(msg)
    
    def log_system(self, event_type, details):
        """
        Log a system event
        
        Parameters:
        -----------
        event_type : str
            Type of system event
        details : str
            Event details
        """
        msg = f"SYSTEM|{event_type}|{details}"
        self.logger.info(msg)
    
    def parse_log_file(self, log_file=None):
        """
        Parse a trade log file into structured data
        
        Parameters:
        -----------
        log_file : str
            Path to log file (optional)
            
        Returns:
        --------
        dict
            Dictionary with parsed log data
        """
        if log_file is None:
            # Use the default log file
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            current_date = datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(logs_dir, f'gann_trading_{current_date}.log')
        
        # Parse the log file
        signals = []
        orders = []
        fills = []
        positions = []
        errors = []
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    parts = line.strip().split('|')
                    
                    if len(parts) < 3:
                        continue
                    
                    timestamp = parts[0]
                    log_type = parts[2]
                    
                    if log_type == 'SIGNAL':
                        signals.append({
                            'timestamp': timestamp,
                            'symbol': parts[3],
                            'timeframe': parts[4],
                            'signal_type': parts[5],
                            'price': float(parts[6]),
                            'gann_level': float(parts[7])
                        })
                    elif log_type == 'ORDER':
                        order = {
                            'timestamp': timestamp,
                            'symbol': parts[3],
                            'order_type': parts[4],
                            'action': parts[5],
                            'quantity': int(parts[6]),
                            'price': float(parts[7])
                        }
                        if len(parts) > 8:
                            order['order_id'] = parts[8]
                        orders.append(order)
                    elif log_type == 'FILL':
                        fills.append({
                            'timestamp': timestamp,
                            'symbol': parts[3],
                            'action': parts[4],
                            'quantity': int(parts[5]),
                            'price': float(parts[6]),
                            'order_id': parts[7],
                            'fill_time': parts[8] if len(parts) > 8 else timestamp
                        })
                    elif log_type.startswith('POSITION'):
                        position = {
                            'timestamp': timestamp,
                            'type': log_type,
                            'symbol': parts[3],
                            'action': parts[4],
                            'quantity': int(parts[5]),
                            'entry_price': float(parts[6])
                        }
                        if log_type == 'POSITION_CLOSE' and len(parts) > 7:
                            position['exit_price'] = float(parts[7])
                            if len(parts) > 8:
                                position['pnl'] = float(parts[8])
                            if len(parts) > 9:
                                position['exit_reason'] = parts[9]
                        positions.append(position)
                    elif log_type == 'ERROR':
                        errors.append({
                            'timestamp': timestamp,
                            'context': parts[3],
                            'message': parts[4]
                        })
        except Exception as e:
            self.logger.error(f"Error parsing log file: {e}")
        
        return {
            'signals': signals,
            'orders': orders,
            'fills': fills,
            'positions': positions,
            'errors': errors
        }

class PerformanceLogger:
    """
    Logger for system performance metrics
    """
    
    def __init__(self, log_dir=None):
        """
        Initialize the performance logger
        
        Parameters:
        -----------
        log_dir : str
            Directory for performance logs (optional)
        """
        self.logger = logging.getLogger('gann_trading.performance')
        
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'performance')
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create a CSV file for daily performance
        self.daily_file = os.path.join(log_dir, 'daily_performance.csv')
        
        # Check if the file exists, if not create with header
        if not os.path.exists(self.daily_file):
            with open(self.daily_file, 'w') as f:
                f.write('date,account_balance,daily_pnl,win_trades,loss_trades,win_rate,profit_factor\n')
    
    def log_daily_performance(self, account_balance, daily_pnl, win_trades, loss_trades):
        """
        Log daily performance metrics
        
        Parameters:
        -----------
        account_balance : float
            End-of-day account balance
        daily_pnl : float
            Daily P&L
        win_trades : int
            Number of winning trades
        loss_trades : int
            Number of losing trades
        """
        date = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate metrics
        total_trades = win_trades + loss_trades
        win_rate = win_trades / total_trades if total_trades > 0 else 0
        profit_factor = 1.0  # Placeholder, would need more data to calculate
        
        # Log to logger
        self.logger.info(f"DAILY_PERFORMANCE|{date}|{account_balance}|{daily_pnl}|{win_trades}|{loss_trades}|{win_rate}")
        
        # Append to CSV
        with open(self.daily_file, 'a') as f:
            f.write(f'{date},{account_balance},{daily_pnl},{win_trades},{loss_trades},{win_rate},{profit_factor}\n')
    
    def log_trade_performance(self, trade_data):
        """
        Log performance metrics for a single trade
        
        Parameters:
        -----------
        trade_data : dict
            Trade data including entry, exit, P&L, etc.
        """
        symbol = trade_data.get('symbol', '')
        entry_time = trade_data.get('entry_time', datetime.now())
        exit_time = trade_data.get('exit_time', datetime.now())
        action = trade_data.get('action', '')
        entry_price = trade_data.get('entry_price', 0)
        exit_price = trade_data.get('exit_price', 0)
        quantity = trade_data.get('quantity', 0)
        pnl = trade_data.get('pnl', 0)
        exit_reason = trade_data.get('exit_reason', '')
        
        # Calculate duration
        duration = (exit_time - entry_time).total_seconds() / 60  # in minutes
        
        # Log to logger
        self.logger.info(f"TRADE_PERFORMANCE|{symbol}|{action}|{entry_price}|{exit_price}|{quantity}|{pnl}|{duration}|{exit_reason}")