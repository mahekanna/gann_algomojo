# -*- coding: utf-8 -*-
"""
Created on Thu Mar 13 07:19:56 2025

@author: mahes
"""

// src/components/SymbolManager.jsx
import React, { useState, useEffect } from 'react';
import { 
  Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, 
  Paper, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Select, MenuItem, FormControl, InputLabel
} from '@mui/material';
import axios from 'axios';

function SymbolManager() {
  const [symbols, setSymbols] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [currentSymbol, setCurrentSymbol] = useState({
    symbol: '',
    description: '',
    type: 'equity',
    timeframe: '1h',
    exchange: 'NSE',
    option_lot_size: 50,
    tv_symbol: '',
    algomojo_symbol: ''
  });
  const [isEditing, setIsEditing] = useState(false);
  
  useEffect(() => {
    fetchSymbols();
  }, []);
  
  const fetchSymbols = async () => {
    try {
      const response = await axios.get('/api/symbols');
      setSymbols(response.data);
    } catch (error) {
      console.error('Error fetching symbols:', error);
    }
  };
  
  const handleOpenDialog = (symbol = null) => {
    if (symbol) {
      setCurrentSymbol(symbol);
      setIsEditing(true);
    } else {
      setCurrentSymbol({
        symbol: '',
        description: '',
        type: 'equity',
        timeframe: '1h',
        exchange: 'NSE',
        option_lot_size: 50,
        tv_symbol: '',
        algomojo_symbol: ''
      });
      setIsEditing(false);
    }
    setOpenDialog(true);
  };
  
  const handleCloseDialog = () => {
    setOpenDialog(false);
  };
  
  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setCurrentSymbol({
      ...currentSymbol,
      [name]: value
    });
  };
  
  const handleSubmit = async () => {
    try {
      if (isEditing) {
        await axios.put(`/api/symbols/${currentSymbol.symbol}`, currentSymbol);
      } else {
        await axios.post('/api/symbols', currentSymbol);
      }
      fetchSymbols();
      handleCloseDialog();
    } catch (error) {
      console.error('Error saving symbol:', error);
    }
  };
  
  const handleDelete = async (symbol) => {
    if (window.confirm(`Are you sure you want to delete ${symbol}?`)) {
      try {
        await axios.delete(`/api/symbols/${symbol}`);
        fetchSymbols();
      } catch (error) {
        console.error('Error deleting symbol:', error);
      }
    }
  };
  
  const handleImport = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      await axios.post('/api/symbols/import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      fetchSymbols();
    } catch (error) {
      console.error('Error importing symbols:', error);
    }
  };
  
  const handleExport = async () => {
    try {
      const response = await axios.get('/api/symbols/export', {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'symbols.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error exporting symbols:', error);
    }
  };
  
  const handleAutoMap = (symbol) => {
    // Auto-generate the other symbol format
    let tv_symbol = currentSymbol.tv_symbol || currentSymbol.symbol;
    let algomojo_symbol = currentSymbol.algomojo_symbol;
    
    if (!algomojo_symbol && tv_symbol) {
      // Generate AlgoMojo symbol from TV symbol
      if (currentSymbol.type === 'equity') {
        algomojo_symbol = `${tv_symbol}-EQ`;
      } else if (currentSymbol.type === 'index') {
        algomojo_symbol = `${tv_symbol}-I`;
      }
      
      setCurrentSymbol({
        ...currentSymbol,
        algomojo_symbol
      });
    }
  };
  
  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Button variant="contained" onClick={() => handleOpenDialog()}>
          Add Symbol
        </Button>
        <Box>
          <Button
            variant="outlined"
            component="label"
            sx={{ mr: 1 }}
          >
            Import CSV
            <input
              type="file"
              hidden
              accept=".csv"
              onChange={handleImport}
            />
          </Button>
          <Button variant="outlined" onClick={handleExport}>
            Export CSV
          </Button>
        </Box>
      </Box>
      
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Symbol</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Exchange</TableCell>
              <TableCell>TradingView</TableCell>
              <TableCell>AlgoMojo</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {symbols.map((symbol) => (
              <TableRow key={symbol.symbol}>
                <TableCell>{symbol.symbol}</TableCell>
                <TableCell>{symbol.description}</TableCell>
                <TableCell>{symbol.type}</TableCell>
                <TableCell>{symbol.exchange}</TableCell>
                <TableCell>{symbol.tv_symbol}</TableCell>
                <TableCell>{symbol.algomojo_symbol}</TableCell>
                <TableCell>
                  <Button size="small" onClick={() => handleOpenDialog(symbol)}>
                    Edit
                  </Button>
                  <Button size="small" color="error" onClick={() => handleDelete(symbol.symbol)}>
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      
      <Dialog open={openDialog} onClose={handleCloseDialog} fullWidth>
        <DialogTitle>{isEditing ? 'Edit Symbol' : 'Add Symbol'}</DialogTitle>
        <DialogContent>
          <Box component="form" sx={{ mt: 2 }}>
            <TextField
              fullWidth
              margin="normal"
              label="Symbol Identifier"
              name="symbol"
              value={currentSymbol.symbol}
              onChange={handleInputChange}
              disabled={isEditing}
            />
            
            <TextField
              fullWidth
              margin="normal"
              label="Description"
              name="description"
              value={currentSymbol.description}
              onChange={handleInputChange}
            />
            
            <FormControl fullWidth margin="normal">
              <InputLabel>Type</InputLabel>
              <Select
                name="type"
                value={currentSymbol.type}
                onChange={handleInputChange}
              >
                <MenuItem value="equity">Equity</MenuItem>
                <MenuItem value="index">Index</MenuItem>
                <MenuItem value="commodity">Commodity</MenuItem>
                <MenuItem value="currency">Currency</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl fullWidth margin="normal">
              <InputLabel>Exchange</InputLabel>
              <Select
                name="exchange"
                value={currentSymbol.exchange}
                onChange={handleInputChange}
              >
                <MenuItem value="NSE">NSE</MenuItem>
                <MenuItem value="BSE">BSE</MenuItem>
                <MenuItem value="MCX">MCX</MenuItem>
                <MenuItem value="NFO">NFO</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl fullWidth margin="normal">
              <InputLabel>Timeframe</InputLabel>
              <Select
                name="timeframe"
                value={currentSymbol.timeframe}
                onChange={handleInputChange}
              >
                <MenuItem value="1m">1 minute</MenuItem>
                <MenuItem value="5m">5 minutes</MenuItem>
                <MenuItem value="15m">15 minutes</MenuItem>
                <MenuItem value="30m">30 minutes</MenuItem>
                <MenuItem value="1h">1 hour</MenuItem>
                <MenuItem value="1d">1 day</MenuItem>
              </Select>
            </FormControl>
            
            <TextField
              fullWidth
              margin="normal"
              label="Option Lot Size"
              name="option_lot_size"
              type="number"
              value={currentSymbol.option_lot_size}
              onChange={handleInputChange}
            />
            
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
              <TextField
                fullWidth
                margin="normal"
                label="TradingView Symbol"
                name="tv_symbol"
                value={currentSymbol.tv_symbol}
                onChange={handleInputChange}
              />
              <TextField
                fullWidth
                margin="normal"
                label="AlgoMojo Symbol"
                name="algomojo_symbol"
                value={currentSymbol.algomojo_symbol}
                onChange={handleInputChange}
                sx={{ ml: 2 }}
              />
              <Button 
                sx={{ ml: 1, height: 40 }} 
                onClick={handleAutoMap}
              >
                Auto Map
              </Button>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained">
            {isEditing ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default SymbolManager;