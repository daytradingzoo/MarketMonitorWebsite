"use client";

import { Card, Title } from "@tremor/react";
import { BlockConfig } from "@/app/lib/types";

interface Props {
  config: BlockConfig;
  data: Record<string, unknown>[];
}

function colorFromValue(value: number, min: number, max: number): string {
  if (max === min) return "bg-gray-700";
  const normalized = (value - min) / (max - min);
  if (normalized > 0.7) return "bg-emerald-700";
  if (normalized > 0.5) return "bg-emerald-900";
  if (normalized > 0.4) return "bg-gray-700";
  if (normalized > 0.2) return "bg-red-900";
  return "bg-red-700";
}

export function HeatmapBlock({ config, data }: Props) {
  const metric = config.metrics[0];
  const groupKey = config.groupBy ?? "sector";

  const values = data.map((d) => Number(d[metric] ?? 0)).filter(isFinite);
  const min = Math.min(...values);
  const max = Math.max(...values);

  return (
    <Card className="bg-gray-900 border-gray-800">
      <Title className="text-gray-200">{config.title}</Title>
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
        {data.map((row, i) => {
          const val = Number(row[metric] ?? 0);
          const label = String(row[groupKey] ?? row.date ?? i);
          const bg = colorFromValue(val, min, max);
          return (
            <div
              key={i}
              className={`${bg} rounded p-3 flex flex-col items-center justify-center min-h-[60px] transition-colors`}
            >
              <span className="text-white text-xs font-medium truncate w-full text-center">
                {label}
              </span>
              <span className="text-white text-sm font-bold">
                {isFinite(val) ? val.toFixed(2) : "—"}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
