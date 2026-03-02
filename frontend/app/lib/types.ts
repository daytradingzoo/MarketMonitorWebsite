/**
 * Core types for the block system.
 * A dashboard page is an array of BlockConfig[].
 * BlockRenderer maps each config to the correct component.
 */

export type BlockType =
  | "LineChart"
  | "AreaChart"
  | "BarChart"
  | "StatCard"
  | "Table"
  | "Heatmap";

export interface DimensionFilter {
  dimension: string;
  value: string;
}

export interface MetricFilter {
  column: string;
  operator: ">=" | "<=" | "=" | ">" | "<";
  value: number;
}

export interface BlockConfig {
  id: string;
  type: BlockType;
  title: string;
  repo: string;
  metrics: string[];
  days?: number;
  universe?: string;
  dimensionFilters?: DimensionFilter[];
  groupBy?: string;
  metricFilters?: MetricFilter[];
  color?: string;
  height?: "sm" | "md" | "lg";
  description?: string;
}
