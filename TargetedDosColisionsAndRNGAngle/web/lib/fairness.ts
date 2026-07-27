// TS mirror of testbed/metrics/fairness.py -- Jain's index + polarization
// index (plan-8 OQ8-1), both scale-free ratios computed from real bucket counts.

export function jainsIndex(values: number[]): number {
  const n = values.length;
  if (n === 0) return 1;
  const total = values.reduce((a, b) => a + b, 0);
  if (total === 0) return 1;
  const sumSquares = values.reduce((a, b) => a + b * b, 0);
  return (total * total) / (n * sumSquares);
}

export function polarizationIndex(values: number[]): number {
  const n = values.length;
  if (n === 0) return 1;
  const total = values.reduce((a, b) => a + b, 0);
  if (total === 0) return 1;
  const mean = total / n;
  return Math.max(...values) / mean;
}
