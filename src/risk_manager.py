# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 23:30:55 2025

@author: mahes
"""

# -*- coding: utf-8 -*-
"""
Risk Manager for Trading System

This module handles position sizing, risk management, and trade validation
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import json
import uuid

class RiskManager:
    """
    Manages risk and position sizing for the trading system
    """
    
    def __init__(self, risk_params: Dict[str, Any]):
        """
        Initialize the risk manager with risk parameters
        
        Parameters:
        -----------
        risk_params : dict
            Risk parameters including:
            - max_risk_per_trade: float
            - max_positions: int
            - max_risk_per_symbol: float
            - max_daily_loss: float
            - max_drawdown: float
            - min_risk_reward: float
        """
        self.logger = logging.getLogger(__name__)
        
        # Set default risk parameters
        self.max_risk_per_trade = risk_params.get('max_risk_per_trade', 0.01)  # 1% of account
        self.max_positions = risk_params.get('max_positions', 5)  # Maximum number of open positions
        self.max_risk_per_symbol = risk_params.get('max_risk_per_symbol', 0.02)  # 2% of account per symbol
        self.max_daily_loss = risk_params.get('max_daily_loss', 0.05)  # 5% daily loss limit
        self.max_drawdown = risk_params.get('max_drawdown', 0.10)  # 10% max drawdown
        self.min_risk_reward = risk_params.get('min_risk_reward', 1.5)  # Minimum risk-reward ratio
        
        # Initialize tracking variables
        self.active_positions = {}  # Tracks open positions
        self.daily_pnl = 0.0  # Tracks daily P&L
        self.peak_balance = 0.0  # Tracks peak account balance
        self.current_balance = 0.0  # Current account balance
        self.total_trades = 0  # Total number of trades executed
        self.winning_trades = 0  # Number of winning trades
        self.losing_trades = 0  # Number of losing trades
        self.total_profit = 0.0  # Total profit
        self.total_loss = 0.0  # Total loss
        
        self.logger.info("Risk Manager initialized with parameters: " + json.dumps(risk_params))
    
    def calculate_position_size(self, account_balance: float, entry_price: float, stop_loss: float) -> int:
        """
        Calculate position size based on risk parameters
        
        Parameters:
        -----------
        account_balance : float
            Current account balance
        entry_price : float
            Entry price of the trade
        stop_loss : float
            Stop loss price level
            
        Returns:
        --------
        int
            Position size (quantity)
        """
        if entry_price <= 0 or stop_loss <= 0:
            self.logger.warning("Invalid prices for position sizing: entry_price={}, stop_loss={}".format(
                entry_price, stop_loss))
            return 0
            
        # Update current balance
        self.current_balance = account_balance
        
        # Update peak balance if necessary
        if account_balance > self.peak_balance:
            self.peak_balance = account_balance
        
        # Calculate risk amount
        risk_amount = account_balance * self.max_risk_per_trade
        
        # Calculate potential loss per share
        if entry_price > stop_loss:  # Long position
            risk_per_share = entry_price - stop_loss
        else:  # Short position
            risk_per_share = stop_loss - entry_price
        
        if risk_per_share <= 0:
            self.logger.warning("Invalid risk per share: {}".format(risk_per_share))
            return 0
        
        # Calculate position size
        position_size = risk_amount / risk_per_share
        
        # Round down to an integer
        position_size = int(position_size)
        
        self.logger.info("Calculated position size: {} units (risk: {:.2f} per unit)".format(
            position_size, risk_per_share))
        
        return position_size
    
    def can_place_trade(self, 
                       symbol: str, 
                       action: str, 
                       quantity: int, 
                       entry_price: float, 
                       stop_loss: float, 
                       target_price: Optional[float] = None) -> Tuple[bool, str]:
        """
        Check if a trade can be placed based on risk parameters
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        action : str
            Trade action (BUY or SELL)
        quantity : int
            Trade quantity
        entry_price : float
            Entry price
        stop_loss : float
            Stop loss price
        target_price : float, optional
            Target price
            
        Returns:
        --------
        (bool, str)
            (can_trade, reason)
        """
        # Check if maximum positions reached
        if len(self.active_positions) >= self.max_positions:
            return False, "Maximum positions reached ({})".format(self.max_positions)
        
        # Check if trade size is valid
        if quantity <= 0:
            return False, "Invalid quantity: {}".format(quantity)
        
        # Check if prices are valid
        if entry_price <= 0 or stop_loss <= 0:
            return False, "Invalid price levels: entry={}, stop={}".format(entry_price, stop_loss)
        
        # Check risk-reward ratio if target is provided
        if target_price is not None:
            if action == 'BUY':
                potential_profit = target_price - entry_price
                potential_loss = entry_price - stop_loss
            else:  # SELL
                potential_profit = entry_price - target_price
                potential_loss = stop_loss - entry_price
                
            if potential_loss <= 0:
                return False, "Invalid potential loss: {}".format(potential_loss)
                
            risk_reward = potential_profit / potential_loss
            
            if risk_reward < self.min_risk_reward:
                return False, "Risk-reward ratio too low: {:.2f} (minimum: {:.2f})".format(
                    risk_reward, self.min_risk_reward)
        
        # Check if total risk per symbol is exceeded
        symbol_positions = [p for p in self.active_positions.values() if p.get('symbol') == symbol]
        
        if symbol_positions:
            total_symbol_risk = sum(p.get('risk_amount', 0) for p in symbol_positions)
            new_risk = self._calculate_trade_risk(entry_price, stop_loss, quantity)
            
            if (total_symbol_risk + new_risk) / self.current_balance > self.max_risk_per_symbol:
                return False, "Maximum risk per symbol exceeded"
        
        # Check if daily loss limit is exceeded
        if self.daily_pnl < -1 * (self.current_balance * self.max_daily_loss):
            return False, "Daily loss limit exceeded"
        
        # Check if drawdown limit is exceeded
        if self.peak_balance > 0:
            current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            
            if current_drawdown > self.max_drawdown:
                return False, "Maximum drawdown exceeded: {:.2f}%".format(current_drawdown * 100)
        
        return True, "Trade validated"
    
    def register_position(self, 
                        order_id: str, 
                        symbol: str, 
                        action: str, 
                        quantity: int, 
                        entry_price: float, 
                        stop_loss: float, 
                        target_price: Optional[float] = None) -> str:
        """
        Register a new position with the risk manager
        
        Parameters:
        -----------
        order_id : str
            Order ID from the broker
        symbol : str
            Trading symbol
        action : str
            Trade action (BUY or SELL)
        quantity : int
            Trade quantity
        entry_price : float
            Entry price
        stop_loss : float
            Stop loss price
        target_price : float, optional
            Target price
            
        Returns:
        --------
        str
            Position ID (same as order ID)
        """
        # Calculate risk amount
        risk_amount = self._calculate_trade_risk(entry_price, stop_loss, quantity)
        
        # Calculate risk-reward ratio
        risk_reward = None
        if target_price is not None and target_price > 0:
            if action == 'BUY':
                potential_profit = (target_price - entry_price) * quantity
                potential_loss = (entry_price - stop_loss) * quantity
            else:  # SELL
                potential_profit = (entry_price - target_price) * quantity
                potential_loss = (stop_loss - entry_price) * quantity
                
            if potential_loss > 0:
                risk_reward = potential_profit / potential_loss
        
        # Generate timestamp
        timestamp = datetime.now().isoformat()
        
        # Register position
        position = {
            'order_id': order_id,
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'current_price': entry_price,
            'risk_amount': risk_amount,
            'risk_reward': risk_reward,
            'unrealized_pnl': 0.0,
            'entry_time': timestamp,
            'last_update': timestamp,
            'status': 'open'
        }
        
        self.active_positions[order_id] = position
        
        self.logger.info("Registered new position: {} {} {} @ {:.2f} (ID: {})".format(
            action, quantity, symbol, entry_price, order_id))
        
        return order_id
    
    def update_position(self, position_id: str, current_price: float) -> Dict[str, Any]:
        """
        Update a position with the current market price
        
        Parameters:
        -----------
        position_id : str
            Position ID to update
        current_price : float
            Current market price
            
        Returns:
        --------
        dict
            Updated position information
        """
        if position_id not in self.active_positions:
            self.logger.warning("Position not found: {}".format(position_id))
            return {}
        
        position = self.active_positions[position_id]
        
        # Update current price
        position['current_price'] = current_price
        
        # Calculate unrealized P&L
        if position['action'] == 'BUY':
            position['unrealized_pnl'] = (current_price - position['entry_price']) * position['quantity']
        else:  # SELL
            position['unrealized_pnl'] = (position['entry_price'] - current_price) * position['quantity']
        
        # Update timestamp
        position['last_update'] = datetime.now().isoformat()
        
        return position
    
    def close_position(self, position_id: str, exit_price: float, reason: str) -> Dict[str, Any]:
        """
        Close a position and record the results
        
        Parameters:
        -----------
        position_id : str
            Position ID to close
        exit_price : float
            Exit price
        reason : str
            Reason for closing the position
            
        Returns:
        --------
        dict
            Closed position information
        """
        if position_id not in self.active_positions:
            self.logger.warning("Position not found for closing: {}".format(position_id))
            return {}
        
        position = self.active_positions[position_id].copy()
        
        # Calculate realized P&L
        if position['action'] == 'BUY':
            realized_pnl = (exit_price - position['entry_price']) * position['quantity']
        else:  # SELL
            realized_pnl = (position['entry_price'] - exit_price) * position['quantity']
        
        # Update position status
        position['status'] = 'closed'
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now().isoformat()
        position['realized_pnl'] = realized_pnl
        position['exit_reason'] = reason
        
        # Update statistics
        self.total_trades += 1
        self.daily_pnl += realized_pnl
        
        if realized_pnl > 0:
            self.winning_trades += 1
            self.total_profit += realized_pnl
        else:
            self.losing_trades += 1
            self.total_loss += abs(realized_pnl)
        
        # Remove from active positions
        del self.active_positions[position_id]
        
        self.logger.info("Closed position: {} {} {} @ {:.2f}, P&L: {:.2f} (ID: {})".format(
            position['action'], position['quantity'], position['symbol'], 
            exit_price, realized_pnl, position_id))
        
        return position
    
    def get_position_status(self, position_id: str) -> Dict[str, Any]:
        """
        Get current status of a position
        
        Parameters:
        -----------
        position_id : str
            Position ID to query
            
        Returns:
        --------
        dict
            Position information
        """
        if position_id not in self.active_positions:
            return {}
        
        return self.active_positions[position_id].copy()
    
    def get_active_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active positions
        
        Returns:
        --------
        dict
            All active positions
        """
        return self.active_positions.copy()
    
    def check_exit_conditions(self, position: Dict[str, Any], current_price: float) -> Tuple[bool, str]:
        """
        Check if position exit conditions are met
        
        Parameters:
        -----------
        position : dict
            Position information
        current_price : float
            Current market price
            
        Returns:
        --------
        (bool, str)
            (should_exit, reason)
        """
        if not position:
            return False, "Invalid position"
        
        symbol = position.get('symbol', '')
        action = position.get('action', '')
        entry_price = position.get('entry_price', 0)
        stop_loss = position.get('stop_loss', 0)
        target_price = position.get('target_price')
        
        # Check for stop loss hit
        if action == 'BUY' and current_price <= stop_loss:
            return True, "Stop loss triggered"
        elif action == 'SELL' and current_price >= stop_loss:
            return True, "Stop loss triggered"
        
        # Check for target price hit
        if target_price is not None:
            if action == 'BUY' and current_price >= target_price:
                return True, "Target price reached"
            elif action == 'SELL' and current_price <= target_price:
                return True, "Target price reached"
        
        return False, "No exit condition met"
    
    def update_account_metrics(self, account_balance: float) -> None:
        """
        Update account metrics
        
        Parameters:
        -----------
        account_balance : float
            Current account balance
        """
        self.current_balance = account_balance
        
        if account_balance > self.peak_balance:
            self.peak_balance = account_balance
    
    def get_trade_statistics(self) -> Dict[str, Any]:
        """
        Get trade performance statistics
        
        Returns:
        --------
        dict
            Trade statistics
        """
        win_rate = self.winning_trades / max(self.total_trades, 1)
        profit_factor = self.total_profit / max(self.total_loss, 1)
        
        drawdown = 0
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'net_profit': self.total_profit - self.total_loss,
            'daily_pnl': self.daily_pnl,
            'drawdown': drawdown,
            'current_positions': len(self.active_positions)
        }
    
    def reset_daily_metrics(self) -> None:
        """
        Reset daily trading metrics (call at the start of each trading day)
        """
        self.daily_pnl = 0.0
    
    def _calculate_trade_risk(self, entry_price: float, stop_loss: float, quantity: int) -> float:
        """
        Calculate the risk amount for a trade
        
        Parameters:
        -----------
        entry_price : float
            Entry price
        stop_loss : float
            Stop loss price
        quantity : int
            Trade quantity
            
        Returns:
        --------
        float
            Risk amount in currency
        """
        if entry_price > stop_loss:  # Long position
            risk_per_unit = entry_price - stop_loss
        else:  # Short position
            risk_per_unit = stop_loss - entry_price
        
        return risk_per_unit * quantity