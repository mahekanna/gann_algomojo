# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 23:38:04 2025

@author: mahes
"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gann Square of 9 Trading System Runner

This script provides a command-line interface to run the Gann trading system
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the application header"""
    print("=" * 60)
    print("              GANN SQUARE OF 9 TRADING SYSTEM")
    print("=" * 60)
    print("A trading system based on W.D. Gann's Square of 9 methodology")
    print("-" * 60)

def print_menu():
    """Print the main menu"""
    print("\nPlease select an option:")
    print("1. Run in Paper Trading mode")
    print("2. Run in Live Trading mode")
    print("3. Run Dashboard")
    print("4. Calculate Gann levels for a symbol")
    print("5. View active positions")
    print("6. Exit")
    print("-" * 60)

def run_paper_trading():
    """Run the system in paper trading mode"""
    clear_screen()
    print_header()
    print("\nStarting Gann Trading System in PAPER TRADING mode...")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    try:
        # Run the paper trading script
        subprocess.run([sys.executable, "run_paper_trading.py"])
    except KeyboardInterrupt:
        print("\nPaper trading stopped by user")
    
    input("\nPress Enter to return to the main menu...")

def run_live_trading():
    """Run the system in live trading mode"""
    clear_screen()
    print_header()
    print("\nStarting Gann Trading System in LIVE TRADING mode...")
    print("WARNING: This will use real money for trading!")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    confirm = input("Are you sure you want to start live trading? (yes/no): ")
    
    if confirm.lower() == 'yes':
        try:
            # Run the live trading script
            subprocess.run([sys.executable, "run_live_trading.py"])
        except KeyboardInterrupt:
            print("\nLive trading stopped by user")
    else:
        print("\nLive trading cancelled")
    
    input("\nPress Enter to return to the main menu...")

def run_dashboard():
    """Run the web dashboard"""
    clear_screen()
    print_header()
    print("\nStarting Gann Trading Dashboard...")
    print("The dashboard will be available at http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    try:
        # Run the dashboard script
        subprocess.run([sys.executable, "gann_dashboard.py"])
    except KeyboardInterrupt:
        print("\nDashboard stopped by user")
    
    input("\nPress Enter to return to the main menu...")

def calculate_gann_levels():
    """Calculate Gann Square of 9 levels for a given price"""
    from src.gann_calculator import GannCalculator
    
    clear_screen()
    print_header()
    print("\nGann Square of 9 Calculator")
    print("-" * 60)
    
    try:
        price = float(input("Enter price to analyze: "))
        
        # Initialize calculator with default parameters
        gann_params = {
            'increments': [0.125, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25],
            'num_values': 20,
            'buffer_percentage': 0.002,
            'include_lower': True
        }
        
        calculator = GannCalculator(gann_params)
        
        # Calculate Gann levels
        results = calculator.calculate(price)
        
        if results:
            print("\nGann Square of 9 Results:")
            print(f"Input Price: {results['input_price']}")
            print(f"Buy Above: {results['buy_above']}")
            print(f"Sell Below: {results['sell_below']}")
            print(f"Stoploss Long: {results['stoploss_long']}")
            print(f"Stoploss Short: {results['stoploss_short']}")
            
            print("\nBuy Targets:")
            for target in results['buy_targets']:
                print(f"  {target['angle']}: {target['price']}")
            
            print("\nSell Targets:")
            for target in results['sell_targets']:
                print(f"  {target['angle']}: {target['price']}")
        else:
            print("\nFailed to calculate Gann levels")
    
    except ValueError:
        print("\nInvalid price format")
    except Exception as e:
        print(f"\nError: {str(e)}")
    
    input("\nPress Enter to return to the main menu...")

def view_positions():
    """View active trading positions"""
    import json
    from pathlib import Path
    
    clear_screen()
    print_header()
    print("\nActive Trading Positions")
    print("-" * 60)
    
    positions_file = Path("positions.json")
    
    if not positions_file.exists():
        print("No positions file found")
    else:
        try:
            with open(positions_file, 'r') as f:
                positions = json.load(f)
            
            if not positions:
                print("No active positions")
            else:
                print(f"Found {len(positions)} active positions:")
                print("\nID | Symbol | Action | Quantity | Entry Price | Current Price | P&L")
                print("-" * 80)
                
                for order_id, position in positions.items():
                    symbol = position.get('symbol', 'N/A')
                    action = position.get('action', 'N/A')
                    quantity = position.get('quantity', 0)
                    entry_price = position.get('entry_price', 0)
                    current_price = position.get('current_price', 0)
                    unrealized_pnl = position.get('unrealized_pnl', 0)
                    
                    print(f"{order_id[:8]} | {symbol} | {action} | {quantity} | {entry_price:.2f} | {current_price:.2f} | {unrealized_pnl:.2f}")
        
        except Exception as e:
            print(f"Error reading positions: {str(e)}")
    
    input("\nPress Enter to return to the main menu...")

def main():
    """Main entry point"""
    while True:
        clear_screen()
        print_header()
        print_menu()
        
        choice = input("Enter your choice (1-6): ")
        
        if choice == '1':
            run_paper_trading()
        elif choice == '2':
            run_live_trading()
        elif choice == '3':
            run_dashboard()
        elif choice == '4':
            calculate_gann_levels()
        elif choice == '5':
            view_positions()
        elif choice == '6':
            clear_screen()
            print("Exiting Gann Trading System. Goodbye!")
            sys.exit(0)
        else:
            input("Invalid choice. Press Enter to try again...")

if __name__ == "__main__":
    main()