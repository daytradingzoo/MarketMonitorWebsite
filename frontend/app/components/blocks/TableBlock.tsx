"use client";

import { Card, Title, Table, TableHead, TableHeaderCell, TableBody, TableRow, TableCell } from "@tremor/react";
import { BlockConfig } from "@/app/lib/types";
import { getMetric } from "@/app/lib/metrics";

interface Props {
  config: BlockConfig;
  data: Record<string, unknown>[];
  onRowClick?: (row: Record<string, unknown>) => void;
}

export function TableBlock({ config, data, onRowClick }: Props) {
  const cols = config.metrics;

  return (
    <Card className="bg-gray-900 border-gray-800">
      <Title className="text-gray-200">{config.title}</Title>
      <Table className="mt-4">
        <TableHead>
          <TableRow>
            {cols.map((m) => (
              <TableHeaderCell key={m} className="text-gray-400 text-xs">
                {getMetric(m)?.label ?? m}
              </TableHeaderCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((row, i) => (
            <TableRow
              key={i}
              className={onRowClick ? "cursor-pointer hover:bg-gray-800" : ""}
              onClick={() => onRowClick?.(row)}
            >
              {cols.map((m) => (
                <TableCell key={m} className="text-gray-200 text-sm">
                  {row[m] !== null && row[m] !== undefined ? String(row[m]) : "—"}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
