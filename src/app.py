# -*- coding: utf-8 -*-
"""
Created on Thu Mar 13 07:24:26 2025

@author: mahes
"""

# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from services.gann.gann_calculator import GannCalculator

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

@app.route('/api/calculate', methods=['POST'])
def calculate_gann():
    data = request.json
    price = data.get('price')
    
    if not price:
        return jsonify({"error": "Price is required"}), 400
    
    # Initialize your Gann calculator
    gann_calculator = GannCalculator({
        "increments": [0.125, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25],
        "num_values": 20,
        "buffer_percentage": 0.002,
        "include_lower": True
    })
    
    # Calculate Gann levels
    results = gann_calculator.calculate(float(price))
    
    return jsonify(results)

@app.route('/api/symbols', methods=['GET'])
def get_symbols():
    # Return list of configured symbols
    symbols = [
        {"symbol": "NIFTY", "type": "index", "exchange": "NSE"},
        {"symbol": "BANKNIFTY", "type": "index", "exchange": "NSE"}
    ]
    return jsonify(symbols)

@app.route('/api/market_data/<symbol>', methods=['GET'])
def get_market_data(symbol):
    # Fetch market data for symbol
    from services.gann.tvdata_handler import TVDataHandler
    
    data_handler = TVDataHandler()
    current_price = data_handler.get_current_price(symbol, "NSE")
    
    return jsonify({"symbol": symbol, "price": current_price})

if __name__ == '__main__':
    app.run(debug=True)