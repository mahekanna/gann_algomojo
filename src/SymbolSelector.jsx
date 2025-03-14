# -*- coding: utf-8 -*-
"""
Created on Wed Mar 12 22:41:38 2025

@author: mahes
"""

// src/components/SymbolSelector.jsx
import React from 'react';
import { FormControl, InputLabel, Select, MenuItem } from '@mui/material';

const SymbolSelector = ({ symbols, selectedSymbol, onSelectSymbol }) => {
  return (
    <FormControl fullWidth>
      <InputLabel>Symbol</InputLabel>
      <Select
        value={selectedSymbol}
        label="Symbol"
        onChange={(e) => onSelectSymbol(e.target.value)}
      >
        {symbols.map(symbol => (
          <MenuItem key={symbol.symbol} value={symbol.symbol}>
            {symbol.symbol} ({symbol.exchange})
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default SymbolSelector;