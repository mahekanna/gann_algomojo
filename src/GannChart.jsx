# -*- coding: utf-8 -*-
"""
Created on Wed Mar 12 22:40:45 2025

@author: mahes
"""

// src/components/GannChart.jsx
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';

const GannChart = ({ data, currentPrice }) => {
  if (!data) return null;
  
  // Prepare chart data
  const chartData = [
    { name: 'Sell Below', value: data.sell_below },
    { name: 'StopLoss Long', value: data.stoploss_long },
    { name: 'Current Price', value: currentPrice },
    { name: 'Buy Above', value: data.buy_above },
    { name: 'StopLoss Short', value: data.stoploss_short }
  ];
  
  // Add target levels
  data.buy_targets.forEach((target, index) => {
    chartData.push({ name: `Buy Target ${index + 1}`, value: target });
  });
  
  return (
    <LineChart width={600} height={300} data={chartData}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="name" />
      <YAxis domain={['auto', 'auto']} />
      <Tooltip />
      <Legend />
      <ReferenceLine y={currentPrice} stroke="green" label="Current" />
      <Line type="monotone" dataKey="value" stroke="#8884d8" />
    </LineChart>
  );
};

export default GannChart;