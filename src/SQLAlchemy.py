# -*- coding: utf-8 -*-
"""
Created on Wed Mar 12 22:42:28 2025

@author: mahes
"""

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gann_trading.db'
db = SQLAlchemy(app)

# Define models
class Symbol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    exchange = db.Column(db.String(20), nullable=False)
    
class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(50), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float)
    quantity = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(10), nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False)
    exit_time = db.Column(db.DateTime)
    pnl = db.Column(db.Float)
    status = db.Column(db.String(20), nullable=False)

# Create tables
with app.app_context():
    db.create_all()