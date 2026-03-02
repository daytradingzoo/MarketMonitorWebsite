"use client";

import { Card, Title, LineChart } from "@tremor/react";
import { BlockConfig } from "@/app/lib/types";
import { getMetric } from "@/app/lib/metrics";

interface Props {
  config: BlockConfig;
  data: Record<string, unknown>[];
}

export function LineChartBlock({ config, data }: Props) {
  const sorted = [...data].reverse(); // API returns DESC; chart needs ASC

  const categories = config.metrics.map((m) => getMetric(m)?.label ?? m);
  const colors = config.metrics.map((m) => getMetric(m)?.color ?? "blue");

  // Remap metric keys to their labels for Tremor
  const chartData = sorted.map((row) => {
    const out: Record<string, unknown> = { date: row.date };
    config.metrics.forEach((m) => {
      const label = getMetric(m)?.label ?? m;
      out[label] = row[m] ?? null;
    });
    return out;
  });

  return (
    <Card className="bg-gray-900 border-gray-800">
      <Title className="text-gray-200">{config.title}</Title>
      <LineChart
        className="mt-4 h-52"
        data={chartData}
        index="date"
        categories={categories}
        colors={colors}
        showLegend={config.metrics.length > 1}
        showGridLines={true}
        curveType="monotone"
        connectNulls={true}
      />
    </Card>
  );
}
