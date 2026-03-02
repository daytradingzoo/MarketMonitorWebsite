/**
 * Home page — Market Overview Dashboard
 * 8 rows powered by BlockConfig arrays and BlockRenderer.
 *
 * Layout:
 *   Row 1 — Market pulse stat cards
 *   Row 2 — Index panel (SPX / NDX / VIX)
 *   Row 3 — Breadth charts (A/D area, McClellan, 52wk hi/lo)
 *   Row 4 — MA breadth stat cards
 *   Row 5 — Momentum / extreme movers
 *   Row 6 — Breakout quality ratios
 *   Row 7 — RSI breadth
 *   Row 8 — Top movers table + RVOL leaders
 */

import { BlockConfig } from "@/app/lib/types";
import { BlockRenderer } from "@/app/components/blocks/BlockRenderer";
import { api } from "@/app/lib/api";
import Link from "next/link";

// ── Row 1: Market pulse ──────────────────────────────────────────────────────
const ROW_1: BlockConfig[] = [
  { id: "adv-stat",    type: "StatCard", title: "Advancing",        repo: "mkt_all", metrics: ["adv"],    universe: "all" },
  { id: "dec-stat",    type: "StatCard", title: "Declining",         repo: "mkt_all", metrics: ["dec"],    universe: "all" },
  { id: "rat-stat",    type: "StatCard", title: "A/D Ratio (1d)",    repo: "mkt_all", metrics: ["rat"],    universe: "all" },
  { id: "rat5-stat",   type: "StatCard", title: "A/D Ratio (5d)",    repo: "mkt_all", metrics: ["rat5"],   universe: "all" },
  { id: "rat10-stat",  type: "StatCard", title: "A/D Ratio (10d)",   repo: "mkt_all", metrics: ["rat10"],  universe: "all" },
  { id: "mcclel-stat", type: "StatCard", title: "McClellan Osc.",    repo: "mkt_all", metrics: ["mcclellan"], universe: "all" },
];

// ── Row 2: Index panel ───────────────────────────────────────────────────────
const ROW_2: BlockConfig[] = [
  { id: "spx-stat",    type: "StatCard", title: "S&P 500",           repo: "mkt_all", metrics: ["spx"],     universe: "all" },
  { id: "spxrsi-stat", type: "StatCard", title: "SPX RSI(14)",       repo: "mkt_all", metrics: ["spxrsi"],  universe: "all" },
  { id: "ndx-stat",    type: "StatCard", title: "Nasdaq 100",        repo: "mkt_all", metrics: ["ndx"],     universe: "all" },
  { id: "ndxrsi-stat", type: "StatCard", title: "NDX RSI(14)",       repo: "mkt_all", metrics: ["ndxrsi"],  universe: "all" },
  { id: "vix-stat",    type: "StatCard", title: "VIX",               repo: "mkt_all", metrics: ["vix"],     universe: "all" },
];

const ROW_2_CHARTS: BlockConfig[] = [
  {
    id: "spx-chart", type: "LineChart", title: "S&P 500 vs MAs",
    repo: "mkt_all", metrics: ["spx", "spx050ma", "spx200ma"],
    universe: "all", days: 252,
  },
  {
    id: "ndx-chart", type: "LineChart", title: "Nasdaq 100 vs MAs",
    repo: "mkt_all", metrics: ["ndx", "ndx050ma", "ndx200ma"],
    universe: "all", days: 252,
  },
  {
    id: "vix-chart", type: "LineChart", title: "VIX (30d)",
    repo: "mkt_all", metrics: ["vix"],
    universe: "all", days: 30,
  },
];

// ── Row 3: Breadth charts ────────────────────────────────────────────────────
const ROW_3: BlockConfig[] = [
  {
    id: "ad-area", type: "AreaChart", title: "Advancing / Declining",
    repo: "mkt_all", metrics: ["adv", "dec"],
    universe: "all", days: 90,
  },
  {
    id: "mcclel-chart", type: "LineChart", title: "McClellan Oscillator",
    repo: "mkt_all", metrics: ["mcclellan"],
    universe: "all", days: 252,
  },
  {
    id: "hilos-chart", type: "LineChart", title: "New 52-Week Highs / Lows",
    repo: "mkt_all", metrics: ["newhi", "newlo"],
    universe: "all", days: 252,
  },
];

// ── Row 4: MA breadth stat cards ─────────────────────────────────────────────
const ROW_4: BlockConfig[] = [
  { id: "a050ma-stat",  type: "StatCard", title: "Above SMA 50",     repo: "mkt_all", metrics: ["a050ma"],  universe: "all" },
  { id: "a200ma-stat",  type: "StatCard", title: "Above SMA 200",    repo: "mkt_all", metrics: ["a200ma"],  universe: "all" },
  { id: "pct200-stat",  type: "StatCard", title: "% Above SMA 200",  repo: "mkt_all", metrics: ["pcta200ma"], universe: "all" },
  { id: "t2108-stat",   type: "StatCard", title: "T2108 (>SMA40)",   repo: "mkt_all", metrics: ["t2108"],   universe: "all" },
  { id: "newhi-stat",   type: "StatCard", title: "New 52-Week Highs",repo: "mkt_all", metrics: ["newhi"],   universe: "all" },
  { id: "newlo-stat",   type: "StatCard", title: "New 52-Week Lows", repo: "mkt_all", metrics: ["newlo"],   universe: "all" },
];

const ROW_4_CHARTS: BlockConfig[] = [
  {
    id: "pct200-chart", type: "LineChart", title: "% Stocks Above SMA 200 (252d)",
    repo: "mkt_all", metrics: ["pcta200ma"],
    universe: "all", days: 252,
  },
  {
    id: "t2108-chart", type: "LineChart", title: "T2108 — % Above SMA 40",
    repo: "mkt_all", metrics: ["t2108"],
    universe: "all", days: 252,
  },
];

// ── Row 5: Momentum / extreme movers ────────────────────────────────────────
const ROW_5: BlockConfig[] = [
  { id: "extremeup-stat", type: "StatCard", title: "Extreme Up",    repo: "mkt_all", metrics: ["extremeup"], universe: "all" },
  { id: "extremedn-stat", type: "StatCard", title: "Extreme Down",  repo: "mkt_all", metrics: ["extremedn"], universe: "all" },
  { id: "up4-stat",       type: "StatCard", title: "Up 4%+",        repo: "mkt_all", metrics: ["up4"],       universe: "all" },
  { id: "dn4-stat",       type: "StatCard", title: "Down 4%+",      repo: "mkt_all", metrics: ["dn4"],       universe: "all" },
  { id: "up25m-stat",     type: "StatCard", title: "Up 25%+ Monthly", repo: "mkt_all", metrics: ["up25m"],  universe: "all" },
  { id: "dn25m-stat",     type: "StatCard", title: "Down 25%+ Monthly", repo: "mkt_all", metrics: ["dn25m"], universe: "all" },
];

const ROW_5_CHARTS: BlockConfig[] = [
  {
    id: "extreme-chart", type: "BarChart", title: "Extreme Candles (90d)",
    repo: "mkt_all", metrics: ["extremeup", "extremedn"],
    universe: "all", days: 90,
  },
  {
    id: "up4dn4-chart", type: "BarChart", title: "Up/Down 4%+ on Volume (90d)",
    repo: "mkt_all", metrics: ["up4", "dn4"],
    universe: "all", days: 90,
  },
];

// ── Row 6: Breakout quality ratios ───────────────────────────────────────────
const ROW_6: BlockConfig[] = [
  { id: "ratbu021-stat", type: "StatCard", title: "Breakout Ratio 21d",  repo: "mkt_all", metrics: ["ratbu021"], universe: "all" },
  { id: "ratbd021-stat", type: "StatCard", title: "Breakdown Ratio 21d", repo: "mkt_all", metrics: ["ratbd021"], universe: "all" },
  { id: "ratbu063-stat", type: "StatCard", title: "Breakout Ratio 63d",  repo: "mkt_all", metrics: ["ratbu063"], universe: "all" },
  { id: "ratbd063-stat", type: "StatCard", title: "Breakdown Ratio 63d", repo: "mkt_all", metrics: ["ratbd063"], universe: "all" },
  { id: "ratbu252-stat", type: "StatCard", title: "Breakout Ratio 252d", repo: "mkt_all", metrics: ["ratbu252"], universe: "all" },
  { id: "ratbd252-stat", type: "StatCard", title: "Breakdown Ratio 252d",repo: "mkt_all", metrics: ["ratbd252"], universe: "all" },
];

// ── Row 7: RSI breadth ───────────────────────────────────────────────────────
const ROW_7: BlockConfig[] = [
  { id: "rsios-stat",  type: "StatCard", title: "RSI Oversold",   repo: "mkt_all", metrics: ["rsios"],    universe: "all" },
  { id: "rsiob-stat",  type: "StatCard", title: "RSI Overbought", repo: "mkt_all", metrics: ["rsiob"],    universe: "all" },
  { id: "ratrsios-stat",type: "StatCard",title: "% Oversold",     repo: "mkt_all", metrics: ["ratrsios"], universe: "all" },
  { id: "ratrsiob-stat",type: "StatCard",title: "% Overbought",   repo: "mkt_all", metrics: ["ratrsiob"], universe: "all" },
];

const ROW_7_CHARTS: BlockConfig[] = [
  {
    id: "rsi-chart", type: "LineChart", title: "RSI Oversold / Overbought Count (252d)",
    repo: "mkt_all", metrics: ["rsios", "rsiob"],
    universe: "all", days: 252,
  },
];

// ── Row 8: Movers tables ─────────────────────────────────────────────────────
// These are fetched separately via the movers API endpoints, not repo data.

async function StatusBadge() {
  let statusText = "Unknown";
  let dataDate = "";
  try {
    const status = await api.status();
    const lastRun = status.last_successful_run as Record<string, unknown> | null;
    dataDate = String(status.latest_data_date ?? "");
    statusText = lastRun ? `Last run: ${lastRun.run_date} (${lastRun.duration_seconds}s)` : "No runs yet";
  } catch {
    statusText = "API offline";
  }
  return (
    <div className="flex items-center gap-4 text-xs text-gray-500">
      <span>Data as of: <span className="text-gray-300">{dataDate || "—"}</span></span>
      <span>{statusText}</span>
    </div>
  );
}

function SectionLabel({ label }: { label: string }) {
  return (
    <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3 mt-6">
      {label}
    </h2>
  );
}

function StatGrid({ configs }: { configs: BlockConfig[] }) {
  return (
    <div className={`grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6`}>
      {configs.map((c) => (
        <BlockRenderer key={c.id} config={c} />
      ))}
    </div>
  );
}

function ChartGrid({ configs, cols = 3 }: { configs: BlockConfig[]; cols?: number }) {
  const colClass = cols === 2 ? "lg:grid-cols-2" : "lg:grid-cols-3";
  return (
    <div className={`grid gap-4 grid-cols-1 sm:grid-cols-2 ${colClass}`}>
      {configs.map((c) => (
        <BlockRenderer key={c.id} config={c} />
      ))}
    </div>
  );
}

export default async function HomePage() {
  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Market Overview</h1>
        <StatusBadge />
      </div>

      {/* Quick links */}
      <div className="flex gap-4 mb-6 text-sm">
        <Link href="/sector/Technology" className="text-blue-400 hover:text-blue-300">
          Technology
        </Link>
        <Link href="/sector/Healthcare" className="text-blue-400 hover:text-blue-300">
          Healthcare
        </Link>
        <Link href="/sector/Financials" className="text-blue-400 hover:text-blue-300">
          Financials
        </Link>
        <Link href="/sector/Energy" className="text-blue-400 hover:text-blue-300">
          Energy
        </Link>
      </div>

      {/* Row 1 — Market Pulse */}
      <SectionLabel label="Market Pulse" />
      <StatGrid configs={ROW_1} />

      {/* Row 2 — Index Panel */}
      <SectionLabel label="Indexes" />
      <StatGrid configs={ROW_2} />
      <div className="mt-4">
        <ChartGrid configs={ROW_2_CHARTS} />
      </div>

      {/* Row 3 — Breadth */}
      <SectionLabel label="Market Breadth" />
      <ChartGrid configs={ROW_3} />

      {/* Row 4 — MA Breadth */}
      <SectionLabel label="Moving Average Breadth" />
      <StatGrid configs={ROW_4} />
      <div className="mt-4">
        <ChartGrid configs={ROW_4_CHARTS} cols={2} />
      </div>

      {/* Row 5 — Momentum */}
      <SectionLabel label="Momentum & Extreme Movers" />
      <StatGrid configs={ROW_5} />
      <div className="mt-4">
        <ChartGrid configs={ROW_5_CHARTS} cols={2} />
      </div>

      {/* Row 6 — Breakout Quality */}
      <SectionLabel label="Breakout Quality Ratios" />
      <StatGrid configs={ROW_6} />

      {/* Row 7 — RSI Breadth */}
      <SectionLabel label="RSI Breadth" />
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        <div className="grid gap-3 grid-cols-2">
          {ROW_7.map((c) => (
            <BlockRenderer key={c.id} config={c} />
          ))}
        </div>
        {ROW_7_CHARTS.map((c) => (
          <div key={c.id} className="lg:col-span-2">
            <BlockRenderer config={c} />
          </div>
        ))}
      </div>

      {/* Row 8 — Top movers */}
      <SectionLabel label="Top Movers" />
      <TopMoversRow />
    </div>
  );
}

async function TopMoversRow() {
  let gainers: Record<string, unknown>[] = [];
  let losers: Record<string, unknown>[] = [];
  let volumeLeaders: Record<string, unknown>[] = [];

  try {
    const movers = await api.movers.topN(15);
    gainers = movers.gainers as Record<string, unknown>[];
    losers  = movers.losers as Record<string, unknown>[];
    volumeLeaders = await api.movers.volume(15) as Record<string, unknown>[];
  } catch {
    return <p className="text-gray-500 text-sm">Movers data unavailable</p>;
  }

  const MoverTable = ({
    rows,
    title,
  }: {
    rows: Record<string, unknown>[];
    title: string;
  }) => (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">{title}</h3>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-1 pr-3">Ticker</th>
            <th className="text-left py-1 pr-3">Name</th>
            <th className="text-right py-1 pr-3">Close</th>
            <th className="text-right py-1">Chg%</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const pct = Number(r.pct_change ?? 0);
            const isUp = pct >= 0;
            return (
              <tr key={i} className="border-b border-gray-800/50">
                <td className="py-1 pr-3 font-medium">
                  <Link
                    href={`/stock/${r.ticker}`}
                    className="text-blue-400 hover:text-blue-300"
                  >
                    {String(r.ticker)}
                  </Link>
                </td>
                <td className="py-1 pr-3 text-gray-400 truncate max-w-[140px]">
                  {String(r.name ?? "")}
                </td>
                <td className="py-1 pr-3 text-right text-gray-200">
                  {Number(r.close).toFixed(2)}
                </td>
                <td className={`py-1 text-right font-medium ${isUp ? "text-emerald-400" : "text-red-400"}`}>
                  {isUp ? "+" : ""}
                  {pct.toFixed(2)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  const VolumeTable = ({ rows }: { rows: Record<string, unknown>[] }) => (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">RVOL Leaders</h3>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-1 pr-3">Ticker</th>
            <th className="text-left py-1 pr-3">Sector</th>
            <th className="text-right py-1 pr-3">RVOL</th>
            <th className="text-right py-1">RSI</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-gray-800/50">
              <td className="py-1 pr-3 font-medium">
                <Link
                  href={`/stock/${r.ticker}`}
                  className="text-blue-400 hover:text-blue-300"
                >
                  {String(r.ticker)}
                </Link>
              </td>
              <td className="py-1 pr-3 text-gray-400 text-xs">
                {String(r.sector ?? "—")}
              </td>
              <td className="py-1 pr-3 text-right text-amber-400">
                {Number(r.rvol).toFixed(1)}x
              </td>
              <td className="py-1 text-right text-gray-300">
                {r.rsi14 ? Number(r.rsi14).toFixed(0) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <MoverTable rows={gainers} title="Top Gainers" />
      <MoverTable rows={losers}  title="Top Losers" />
      <VolumeTable rows={volumeLeaders} />
    </div>
  );
}
