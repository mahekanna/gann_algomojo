import subprocess
import sys
import os

if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Run the main script with live mode
    subprocess.run([sys.executable, "gann_trading_system.py", "--mode", "live"])
