/**
 * Stock detail page — /stock/AAPL
 * Shows individual stock metrics and price chart.
 */

import { api } from "@/app/lib/api";
import Link from "next/link";

interface Props {
  params: { ticker: string };
}

function MetricRow({ label, value }: { label: string; value: unknown }) {
  const formatted =
    value === null || value === undefined
      ? "—"
      : typeof value === "number"
      ? value.toLocaleString("en-US", { maximumFractionDigits: 4 })
      : String(value);
  return (
    <div className="flex justify-between py-2 border-b border-gray-800 text-sm">
      <span className="text-gray-400">{label}</span>
      <span className="text-gray-200 font-medium">{formatted}</span>
    </div>
  );
}

export default async function StockPage({ params }: Props) {
  const ticker = params.ticker.toUpperCase();

  let stock: Record<string, unknown> = {};
  let bars: Record<string, unknown>[] = [];

  try {
    stock = await api.stock.detail(ticker);
    bars = await api.stock.bars(ticker, 252) as Record<string, unknown>[];
  } catch {
    return (
      <div className="text-gray-400">
        <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">
          ← Back to Overview
        </Link>
        <p className="mt-6">No data available for {ticker}.</p>
      </div>
    );
  }

  const lastBar = bars[0] ?? {};
  const priorBar = bars[1] ?? {};
  const pctChange =
    lastBar.close && priorBar.close
      ? (((Number(lastBar.close) - Number(priorBar.close)) / Number(priorBar.close)) * 100).toFixed(2)
      : null;

  const isUp = pctChange ? Number(pctChange) >= 0 : null;

  return (
    <div className="max-w-5xl mx-auto">
      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">
        ← Market Overview
      </Link>

      {/* Header */}
      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">{ticker}</h1>
          {stock.name && (
            <p className="text-gray-400 mt-1">{String(stock.name)}</p>
          )}
          <div className="flex gap-3 mt-2">
            {stock.sector && (
              <Link
                href={`/sector/${encodeURIComponent(String(stock.sector))}`}
                className="text-xs bg-gray-800 text-gray-300 rounded px-2 py-1 hover:bg-gray-700"
              >
                {String(stock.sector)}
              </Link>
            )}
            {stock.exchange && (
              <span className="text-xs bg-gray-800 text-gray-400 rounded px-2 py-1">
                {String(stock.exchange)}
              </span>
            )}
          </div>
        </div>

        <div className="text-right">
          <span className="text-3xl font-bold text-white">
            ${Number(lastBar.close ?? 0).toFixed(2)}
          </span>
          {pctChange && (
            <p className={`text-lg font-medium mt-1 ${isUp ? "text-emerald-400" : "text-red-400"}`}>
              {isUp ? "+" : ""}
              {pctChange}%
            </p>
          )}
          <p className="text-gray-500 text-xs mt-1">
            {String(lastBar.date ?? "")}
          </p>
        </div>
      </div>

      {/* Metrics grid */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Price & Volume
          </h2>
          <MetricRow label="Open"   value={lastBar.open} />
          <MetricRow label="High"   value={lastBar.high} />
          <MetricRow label="Low"    value={lastBar.low} />
          <MetricRow label="Close"  value={lastBar.close} />
          <MetricRow label="VWAP"   value={lastBar.vwap} />
          <MetricRow label="Volume" value={lastBar.volume} />
          <MetricRow label="RVOL"   value={stock.rvol} />
        </div>

        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Technical Indicators
          </h2>
          <MetricRow label="RSI(14)"    value={stock.rsi14} />
          <MetricRow label="ATR(14)"    value={stock.atr14} />
          <MetricRow label="ATR(21)"    value={stock.atr21} />
          <MetricRow label="IBS"        value={stock.ibs} />
          <MetricRow label="SMA 20"     value={stock.sma20} />
          <MetricRow label="SMA 50"     value={stock.sma50} />
          <MetricRow label="SMA 200"    value={stock.sma200} />
          <MetricRow label="52W High"   value={stock.hhv252} />
          <MetricRow label="52W Low"    value={stock.llv252} />
        </div>
      </div>

      {/* Recent price history */}
      <div className="mt-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Recent Price History (Last 30 Days)
        </h2>
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left py-2 px-3">Date</th>
                <th className="text-right py-2 px-3">Open</th>
                <th className="text-right py-2 px-3">High</th>
                <th className="text-right py-2 px-3">Low</th>
                <th className="text-right py-2 px-3">Close</th>
                <th className="text-right py-2 px-3">Volume</th>
              </tr>
            </thead>
            <tbody>
              {bars.slice(0, 30).map((b, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-1.5 px-3 text-gray-400">{String(b.date)}</td>
                  <td className="py-1.5 px-3 text-right text-gray-300">{Number(b.open).toFixed(2)}</td>
                  <td className="py-1.5 px-3 text-right text-emerald-400">{Number(b.high).toFixed(2)}</td>
                  <td className="py-1.5 px-3 text-right text-red-400">{Number(b.low).toFixed(2)}</td>
                  <td className="py-1.5 px-3 text-right text-white font-medium">{Number(b.close).toFixed(2)}</td>
                  <td className="py-1.5 px-3 text-right text-gray-400">{Number(b.volume).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
