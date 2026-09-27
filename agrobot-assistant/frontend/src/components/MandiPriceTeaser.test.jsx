import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import MandiPriceTeaser from './MandiPriceTeaser';
import ApiService from '../services/api';

jest.mock('../services/api', () => ({
  getMandiCurrent: jest.fn(),
  getMandiTrend: jest.fn(),
}));

test('a mandi timeout is contained inside the optional widget', async () => {
  ApiService.getMandiCurrent.mockRejectedValueOnce(new Error('timeout of 30000ms exceeded'));

  render(
    <MemoryRouter>
      <MandiPriceTeaser
        farmId={1}
        crops={[{ name: 'Rice' }]}
        onAddCrop={() => {}}
      />
    </MemoryRouter>
  );

  await waitFor(() => {
    expect(screen.getByText(/Market prices are temporarily unavailable/)).toBeInTheDocument();
  });
});
