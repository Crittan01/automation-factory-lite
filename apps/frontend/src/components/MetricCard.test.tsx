import React from 'react';
import { render, screen } from '@testing-library/react';

import { MetricCard } from './MetricCard';

describe('MetricCard', () => {
  it('renders title and value', () => {
    render(<MetricCard title="Solicitudes" value={12} subtitle="total" />);
    expect(screen.getByText('Solicitudes')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('total')).toBeInTheDocument();
  });
});
