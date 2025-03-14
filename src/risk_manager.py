# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 21:38:03 2025

@author: mahes
"""

# src/risk_manager.py

import logging
import math
from datetime import datetime, timedelta

class RiskManager:
    """
    Handles risk management, position sizing, and money management
    """
    
    def __init__(self, risk_params):
        """
        Initialize the risk manager with risk parameters
        
        Parameters:
        -----------
        risk_params : dict
            Dictionary containing risk management parameters
            - max_risk_per_trade: Maximum risk per trade as % of account (e.g., 0.01 for 1%)
            - max_positions: Maximum number of concurrent positions
            - max_risk_per_symbol: Maximum risk per symbol as % of account
            - max_daily_loss: Maximum daily loss as % of account
            - max_drawdown: Maximum drawdown as % of account
            - min_risk_reward: Minimum risk-reward ratio for trades
        """
        self.logger = logging.getLogger(__name__)
        
        # Set risk parameters with defaults
        self.max_risk_per_trade = risk_params.get('max_risk_per_trade', 0.01)  # 1% risk per trade
        self.max_positions = risk_params.get('max_positions', 5)
        self.max_risk_per_symbol = risk_params.get('max_risk_per_symbol', 0.02)  # 2% risk per symbol
        self.max_daily_loss = risk_params.get('max_daily_loss', 0.05)  # 5% max daily loss
        self.max_drawdown = risk_params.get('max_drawdown', 0.10)  # 10% max drawdown
        self.min_risk_reward = risk_params.get('min_risk_reward', 1.5)  # 1.5:1 risk-reward
        
        # Track positions and performance
        self.positions = {}
        self.daily_pnl = 0
        self.account_high = 0
        self.current_drawdown = 0
        self.trade_history = []
        
        # Date tracking
        self.current_date = datetime.now().date()
    
    def calculate_position_size(self, account_balance, entry_price, stop_loss):
        """
        Calculate position size based on risk parameters
        
        Parameters:
        -----------
        account_balance : float
            Current account balance
        entry_price : float
            Entry price
        stop_loss : float
            Stop loss price
            
        Returns:
        --------
        int
            Position size (number of shares/contracts)
        """
        try:
            # If no stop loss is provided, cannot calculate position size
            if stop_loss is None or stop_loss == 0 or entry_price == 0:
                self.logger.warning("Invalid stop loss or entry price, cannot calculate position size")
                return 0
            
            # Calculate risk per share
            risk_per_unit = abs(entry_price - stop_loss)
            
            if risk_per_unit == 0:
                self.logger.warning("Risk per unit is zero, cannot calculate position size")
                return 0
            
            # Calculate maximum risk amount
            risk_amount = account_balance * self.max_risk_per_trade
            
            # Calculate position size based on risk
            position_size = risk_amount / risk_per_unit
            
            # Round down to nearest integer
            position_size = math.floor(position_size)
            
            # Log calculation details
            self.logger.info(f"Position size calculation: Account={account_balance}, Risk={self.max_risk_per_trade*100}%, "
                            f"Entry={entry_price}, Stop={stop_loss}, Units={position_size}")
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0
    
    def can_place_trade(self, symbol, action, quantity, entry_price, stop_loss, target_price=None):
        """
        Check if a trade can be placed based on risk parameters
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
        action : str
            "BUY" or "SELL"
        quantity : int
            Order quantity
        entry_price : float
            Entry price
        stop_loss : float
            Stop loss price
        target_price : float
            Target price (optional)
            
        Returns:
        --------
        tuple
            (bool, str) - (Can place trade, reason if not)
        """
        try:
            # Check daily loss limit
            if self.daily_pnl < -self.max_daily_loss:
                return False, f"Daily loss limit of {self.max_daily_loss*100}% reached"
            
            # Check drawdown limit
            if self.current_drawdown > self.max_drawdown:
                return False, f"Max drawdown of {self.max_drawdown*100}% reached"
            
            # Check maximum number of positions
            if len(self.positions) >= self.max_positions:
                return False, f"Maximum number of positions ({self.max_positions}) reached"
            
            # Check risk-reward ratio if target price is provided
            if target_price is not None:
                risk = abs(entry_price - stop_loss)
                reward = abs(target_price - entry_price)
                
                if risk == 0:
                    return False, "Invalid risk (zero)"
                
                risk_reward = reward / risk
                
                if risk_reward < self.min_risk_reward:
                    return False, f"Risk-reward ratio ({risk_reward:.2f}) below minimum ({self.min_risk_reward})"
            
            # Check risk per symbol
            # TODO: Implement symbol-specific risk tracking
            
            # All checks passed
            return True, "Trade permitted"
            
        except Exception as e:
            self.logger.error(f"Error checking trade permission: {e}")
            return False, f"Error in risk check: {str(e)}"
    
    def register_position(self, order_id, symbol, action, quantity, entry_price, stop_loss, target_price=None):
        """
        Register a new position with the risk manager
        
        Parameters:
        -----------
        order_id : str
            Order ID
        symbol : str
            Trading symbol
        action : str
            "BUY" or "SELL"
        quantity : int
            Position size
        entry_price : float
            Entry price
        stop_loss : float
            Stop loss price
        target_price : float
            Target price (optional)
        """
        position = {
            'order_id': order_id,
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'entry_price': entry_price,
            'current_price': entry_price,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'entry_time': datetime.now(),
            'open_pnl': 0,
            'status': 'OPEN'
        }
        
        self.positions[order_id] = position
        self.logger.info(f"Position registered: {symbol} {action} {quantity} @ {entry_price}")
    
    def update_position(self, order_id, current_price, stop_loss=None, target_price=None):
        """
        Update an existing position
        
        Parameters:
        -----------
        order_id : str
            Order ID
        current_price : float
            Current market price
        stop_loss : float
            New stop loss price (optional)
        target_price : float
            New target price (optional)
            
        Returns:
        --------
        dict
            Updated position information
        """
        if order_id not in self.positions:
            self.logger.warning(f"Position {order_id} not found for update")
            return None
        
        position = self.positions[order_id]
        
        # Update price and PnL
        position['current_price'] = current_price
        
        # Calculate open P&L
        if position['action'] == 'BUY':
            position['open_pnl'] = (current_price - position['entry_price']) * position['quantity']
        else:  # SELL
            position['open_pnl'] = (position['entry_price'] - current_price) * position['quantity']
        
        # Update stop loss if provided
        if stop_loss is not None:
            position['stop_loss'] = stop_loss
        
        # Update target price if provided
        if target_price is not None:
            position['target_price'] = target_price
        
        self.logger.debug(f"Position updated: {order_id}, Price: {current_price}, P&L: {position['open_pnl']}")
        
        return position
    
    def close_position(self, order_id, exit_price, exit_reason):
        """
        Close a position and update performance metrics
        
        Parameters:
        -----------
        order_id : str
            Order ID
        exit_price : float
            Exit price
        exit_reason : str
            Reason for exit (e.g., "Stop Loss", "Target", "Manual")
            
        Returns:
        --------
        dict
            Closed position information
        """
        if order_id not in self.positions:
            self.logger.warning(f"Position {order_id} not found for closing")
            return None
        
        position = self.positions[order_id]
        
        # Calculate realized P&L
        if position['action'] == 'BUY':
            realized_pnl = (exit_price - position['entry_price']) * position['quantity']
        else:  # SELL
            realized_pnl = (position['entry_price'] - exit_price) * position['quantity']
        
        # Update position
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now()
        position['exit_reason'] = exit_reason
        position['realized_pnl'] = realized_pnl
        position['status'] = 'CLOSED'
        
        # Update daily P&L
        self.daily_pnl += realized_pnl
        
        # Record trade in history
        self.trade_history.append({
            'order_id': order_id,
            'symbol': position['symbol'],
            'action': position['action'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'quantity': position['quantity'],
            'entry_time': position['entry_time'],
            'exit_time': position['exit_time'],
            'pnl': realized_pnl,
            'exit_reason': exit_reason
        })
        
        # Remove from active positions
        del self.positions[order_id]
        
        self.logger.info(f"Position closed: {order_id}, Exit: {exit_price}, P&L: {realized_pnl}, Reason: {exit_reason}")
        
        return position
    
    def update_account_metrics(self, account_balance):
        """
        Update account metrics for risk management
        
        Parameters:
        -----------
        account_balance : float
            Current account balance
        """
        # Check if it's a new day
        today = datetime.now().date()
        if today != self.current_date:
            # Reset daily tracking
            self.daily_pnl = 0
            self.current_date = today
        
        # Update account high water mark
        if account_balance > self.account_high:
            self.account_high = account_balance
        
        # Calculate current drawdown
        if self.account_high > 0:
            self.current_drawdown = (self.account_high - account_balance) / self.account_high
        
        self.logger.debug(f"Account metrics updated: Balance={account_balance}, "
                         f"Daily P&L={self.daily_pnl}, Drawdown={self.current_drawdown*100:.2f}%")
    
    def get_position_status(self, order_id):
        """
        Get status of a specific position
        
        Parameters:
        -----------
        order_id : str
            Order ID
            
        Returns:
        --------
        dict
            Position information
        """
        if order_id in self.positions:
            return self.positions[order_id]
        else:
            # Check in trade history
            for trade in self.trade_history:
                if trade['order_id'] == order_id:
                    return trade
            
            return None
    
    def get_active_positions(self):
        """
        Get all active positions
        
        Returns:
        --------
        dict
            Dictionary of active positions
        """
        return self.positions
    
    def get_positions_by_symbol(self, symbol):
        """
        Get active positions for a specific symbol
        
        Parameters:
        -----------
        symbol : str
            Trading symbol
            
        Returns:
        --------
        list
            List of positions for the symbol
        """
        return [p for p in self.positions.values() if p['symbol'] == symbol]
    
    def get_trade_statistics(self):
        """
        Get trade statistics
        
        Returns:
        --------
        dict
            Dictionary with trade statistics
        """
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'avg_risk_reward': 0
            }
        
        # Calculate statistics
        total_trades = len(self.trade_history)
        winning_trades = [t for t in self.trade_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trade_history if t['pnl'] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        avg_profit = sum(t['pnl'] for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / loss_count if loss_count > 0 else 0
        
        total_profit = sum(t['pnl'] for t in winning_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Return statistics
        return {
            'total_trades': total_trades,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': total_profit - total_loss
        }
    
    def check_exit_conditions(self, position, current_price):
        """
        Check if a position should be exited based on price conditions
        
        Parameters:
        -----------
        position : dict
            Position information
        current_price : float
            Current market price
            
        Returns:
        --------
        tuple
            (bool, str) - (Should exit, reason for exit)
        """
        # Validate position
        if 'action' not in position or 'stop_loss' not in position:
            return False, "Invalid position data"
        
        # Check stop loss
        if position['action'] == 'BUY' and current_price <= position['stop_loss']:
            return True, "Stop Loss"
        elif position['action'] == 'SELL' and current_price >= position['stop_loss']:
            return True, "Stop Loss"
        
        # Check target price if defined
        if 'target_price' in position and position['target_price'] is not None:
            if position['action'] == 'BUY' and current_price >= position['target_price']:
                return True, "Target Reached"
            elif position['action'] == 'SELL' and current_price <= position['target_price']:
                return True, "Target Reached"
        
        # No exit conditions met
        return False, None