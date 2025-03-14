# -*- coding: utf-8 -*-
"""
Created on Thu Mar 13 07:21:14 2025

@author: mahes
"""

// src/components/SymbolConverter.jsx
import React, { useState } from 'react';
import { Box, TextField, Button, Paper, Typography, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import axios from 'axios';

function SymbolConverter() {
  const [sourceSymbol, setSourceSymbol] = useState('');
  const [sourcePlatform, setSourcePlatform] = useState('tv');
  const [targetPlatform, setTargetPlatform] = useState('algomojo');
  const [result, setResult] = useState('');
  
  const handleConvert = async () => {
    try {
      const response = await axios.get(`/api/symbols/convert`, {
        params: {
          symbol: sourceSymbol,
          from: sourcePlatform,
          to: targetPlatform
        }
      });
      
      setResult(response.data.result);
    } catch (error) {
      console.error('Error converting symbol:', error);
      setResult('Error: Could not convert symbol');
    }
  };
  
  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Symbol Converter
      </Typography>
      
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <TextField
          label="Symbol"
          value={sourceSymbol}
          onChange={(e) => setSourceSymbol(e.target.value)}
          size="small"
          sx={{ flexGrow: 1 }}
        />
        
        <FormControl sx={{ ml: 2, minWidth: 120 }} size="small">
          <InputLabel>From</InputLabel>
          <Select
            value={sourcePlatform}
            onChange={(e) => setSourcePlatform(e.target.value)}
            label="From"
          >
            <MenuItem value="tv">TradingView</MenuItem>
            <MenuItem value="algomojo">AlgoMojo</MenuItem>
          </Select>
        </FormControl>
        
        <FormControl sx={{ ml: 2, minWidth: 120 }} size="small">
          <InputLabel>To</InputLabel>
          <Select
            value={targetPlatform}
            onChange={(e) => setTargetPlatform(e.target.value)}
            label="To"
          >
            <MenuItem value="tv">TradingView</MenuItem>
            <MenuItem value="algomojo">AlgoMojo</MenuItem>
          </Select>
        </FormControl>
        
        <Button variant="contained" onClick={handleConvert} sx={{ ml: 2 }}>
          Convert
        </Button>
      </Box>
      
      {result && (
        <Box sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
          <Typography variant="body1">
            <strong>Result:</strong> {result}
          </Typography>
        </Box>
      )}
    </Paper>
  );
}

export default SymbolConverter;