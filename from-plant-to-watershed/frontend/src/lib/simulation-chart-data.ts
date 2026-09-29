import type { SwatComparisonMonth } from "../types/simulation";

export type DatedMonthlyComparison = SwatComparisonMonth & { month: string };

/** Normalize the date field used by live comparisons and historical SWAT imports. */
export function datedMonthlyComparisonRows(rows: SwatComparisonMonth[]): DatedMonthlyComparison[] {
  return rows.flatMap((row) => {
    const month = row.month || row.period;
    return month ? [{ ...row, month }] : [];
  });
}
