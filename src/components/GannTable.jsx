# -*- coding: utf-8 -*-
"""
Created on Thu Mar 13 07:23:18 2025

@author: mahes
"""

// src/components/GannTable.jsx
import React from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';

const GannTable = ({ values }) => {
  if (!values) return null;
  
  const angles = Object.keys(values);
  const maxRows = Math.max(...angles.map(angle => values[angle].length));
  
  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Index</TableCell>
            {angles.map(angle => (
              <TableCell key={angle}>{angle}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {Array.from({ length: maxRows }).map((_, index) => (
            <TableRow key={index}>
              <TableCell>{index + 1}</TableCell>
              {angles.map(angle => (
                <TableCell key={`${angle}-${index}`}>
                  {values[angle][index] || ''}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default GannTable;