"use client";

import { Card, Metric, Text, Badge } from "@tremor/react";
import { BlockConfig } from "@/app/lib/types";
import { getMetric } from "@/app/lib/metrics";

interface Props {
  config: BlockConfig;
  data: Record<string, unknown>;
}

function formatValue(value: unknown, formatAs?: string): string {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (isNaN(num)) return String(value);
  if (formatAs === "percent") return `${(num * 100).toFixed(1)}%`;
  if (formatAs === "ratio") return num.toFixed(2);
  if (formatAs === "price") return num.toLocaleString("en-US", { minimumFractionDigits: 2 });
  return num.toLocaleString("en-US", { maximumFractionDigits: 1 });
}

export function StatCardBlock({ config, data }: Props) {
  const metric = config.metrics[0];
  const def = getMetric(metric);
  const value = data?.[metric];

  return (
    <Card className="bg-gray-900 border-gray-800">
      <Text className="text-gray-400 text-xs uppercase tracking-wider">
        {config.title}
      </Text>
      <Metric className="text-white mt-1">
        {formatValue(value, def?.formatAs)}
      </Metric>
      {def?.description && (
        <Text className="text-gray-500 text-xs mt-1">{def.description}</Text>
      )}
    </Card>
  );
}
