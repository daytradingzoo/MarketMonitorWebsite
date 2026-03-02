/**
 * BlockRenderer — maps a BlockConfig to the correct chart component.
 * Fetches data from the API and passes it down to the appropriate block.
 * This is a Server Component by default; individual blocks are "use client".
 */

import { BlockConfig } from "@/app/lib/types";
import { api } from "@/app/lib/api";
import { LineChartBlock } from "./LineChartBlock";
import { AreaChartBlock } from "./AreaChartBlock";
import { BarChartBlock } from "./BarChartBlock";
import { StatCardBlock } from "./StatCardBlock";
import { TableBlock } from "./TableBlock";
import { HeatmapBlock } from "./HeatmapBlock";

interface Props {
  config: BlockConfig;
}

export async function BlockRenderer({ config }: Props) {
  let data: Record<string, unknown>[] = [];
  let singleRow: Record<string, unknown> = {};

  try {
    if (config.type === "StatCard") {
      // Stat cards only need the latest row
      const rows = await api.repos.data(config.repo, config.metrics, {
        days: 1,
        universe: config.universe ?? "all",
      });
      singleRow = rows?.[0] ?? {};
    } else {
      data = await api.repos.data(config.repo, config.metrics, {
        days: config.days ?? 252,
        universe: config.universe ?? "all",
        group_by: config.groupBy,
      });
    }
  } catch {
    // Render empty state on error — don't crash the whole page
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 text-gray-500 text-sm">
        {config.title} — data unavailable
      </div>
    );
  }

  switch (config.type) {
    case "LineChart":
      return <LineChartBlock config={config} data={data} />;
    case "AreaChart":
      return <AreaChartBlock config={config} data={data} />;
    case "BarChart":
      return <BarChartBlock config={config} data={data} />;
    case "StatCard":
      return <StatCardBlock config={config} data={singleRow} />;
    case "Table":
      return <TableBlock config={config} data={data} />;
    case "Heatmap":
      return <HeatmapBlock config={config} data={data} />;
    default:
      return null;
  }
}
