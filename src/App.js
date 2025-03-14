# -*- coding: utf-8 -*-
"""
Created on Wed Mar 12 22:37:11 2025

@author: mahes
"""

// src/App.js
import React, { useState, useEffect } from 'react';
import { Container, Typography, Box, Grid, Paper, TextField, Button } from '@mui/material';
import axios from 'axios';
import GannTable from './components/GannTable';
import GannChart from './components/GannChart';
import SymbolSelector from './components/SymbolSelector';

function App() {
  const [symbols, setSymbols] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [currentPrice, setCurrentPrice] = useState(0);
  const [manualPrice, setManualPrice] = useState('');
  const [gannData, setGannData] = useState(null);
  
  // Fetch available symbols
  useEffect(() => {
    axios.get('http://localhost:5000/api/symbols')
      .then(response => {
        setSymbols(response.data);
        if (response.data.length > 0) {
          setSelectedSymbol(response.data[0].symbol);
        }
      })
      .catch(error => console.error('Error fetching symbols:', error));
  }, []);
  
  // Fetch market data when symbol changes
  useEffect(() => {
    if (selectedSymbol) {
      axios.get(`http://localhost:5000/api/market_data/${selectedSymbol}`)
        .then(response => {
          setCurrentPrice(response.data.price);
          calculateGann(response.data.price);
        })
        .catch(error => console.error('Error fetching market data:', error));
    }
  }, [selectedSymbol]);
  
  const calculateGann = (price) => {
    axios.post('http://localhost:5000/api/calculate', { price })
      .then(response => {
        setGannData(response.data);
      })
      .catch(error => console.error('Error calculating Gann levels:', error));
  };
  
  const handleManualCalculate = () => {
    if (manualPrice) {
      calculateGann(parseFloat(manualPrice));
    }
  };
  
  return (
    <Container maxWidth="lg">
      <Typography variant="h4" gutterBottom>
        Gann Square of 9 Trading System
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Symbol Selection</Typography>
            <SymbolSelector 
              symbols={symbols} 
              selectedSymbol={selectedSymbol}
              onSelectSymbol={setSelectedSymbol} 
            />
            
            <Box mt={3}>
              <Typography>Current Price: {currentPrice}</Typography>
              
              <Box mt={2}>
                <TextField 
                  label="Manual Price" 
                  value={manualPrice}
                  onChange={(e) => setManualPrice(e.target.value)}
                  type="number"
                  size="small"
                  fullWidth
                />
                <Button 
                  variant="contained" 
                  onClick={handleManualCalculate}
                  sx={{ mt: 1 }}
                >
                  Calculate
                </Button>
              </Box>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Gann Levels</Typography>
            {gannData ? (
              <>
                <Box my={2}>
                  <Typography>Buy Above: {gannData.buy_above}</Typography>
                  <Typography>Sell Below: {gannData.sell_below}</Typography>
                  <Typography>StopLoss Long: {gannData.stoploss_long}</Typography>
                  <Typography>StopLoss Short: {gannData.stoploss_short}</Typography>
                </Box>
                <GannChart data={gannData} currentPrice={currentPrice} />
              </>
            ) : (
              <Typography>Select a symbol or enter a price to calculate Gann levels</Typography>
            )}
          </Paper>
        </Grid>
        
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Gann Square of 9 Table</Typography>
            {gannData && (
              <GannTable values={gannData.gann_values} />
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

export default App;