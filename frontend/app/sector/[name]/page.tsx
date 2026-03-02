/**
 * Sector drill-down page — /sector/Technology
 * Shows all stocks in a sector sorted by day performance.
 */

import { api } from "@/app/lib/api";
import Link from "next/link";

interface Props {
  params: { name: string };
}

export default async function SectorPage({ params }: Props) {
  const sectorName = decodeURIComponent(params.name);

  let stocks: Record<string, unknown>[] = [];
  let sectorSummary: Record<string, unknown> | undefined;

  try {
    stocks = await api.sectors.byName(sectorName, 200) as Record<string, unknown>[];
    const allSectors = await api.sectors.all() as Record<string, unknown>[];
    sectorSummary = allSectors.find(
      (s) => String(s.sector).toLowerCase() === sectorName.toLowerCase()
    );
  } catch {
    return (
      <div className="text-gray-400">
        <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">
          ← Back to Overview
        </Link>
        <p className="mt-6">No data available for sector: {sectorName}.</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">
        ← Market Overview
      </Link>

      {/* Header */}
      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">{sectorName}</h1>
          <p className="text-gray-400 mt-1">Sector performance</p>
        </div>

        {sectorSummary && (
          <div className="flex gap-6">
            <div className="text-center">
              <p className="text-xs text-gray-500">Avg Change</p>
              <p
                className={`text-xl font-bold ${
                  Number(sectorSummary.avg_pct_change) >= 0
                    ? "text-emerald-400"
                    : "text-red-400"
                }`}
              >
                {Number(sectorSummary.avg_pct_change) >= 0 ? "+" : ""}
                {Number(sectorSummary.avg_pct_change).toFixed(2)}%
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">Advancing</p>
              <p className="text-xl font-bold text-emerald-400">
                {String(sectorSummary.advancing)}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">Declining</p>
              <p className="text-xl font-bold text-red-400">
                {String(sectorSummary.declining)}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">Avg RVOL</p>
              <p className="text-xl font-bold text-amber-400">
                {Number(sectorSummary.avg_rvol).toFixed(1)}x
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Stock table */}
      <div className="mt-6 bg-gray-900 border border-gray-800 rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800 text-xs">
              <th className="text-left py-2.5 px-3">Ticker</th>
              <th className="text-left py-2.5 px-3">Name</th>
              <th className="text-left py-2.5 px-3">Industry</th>
              <th className="text-right py-2.5 px-3">Close</th>
              <th className="text-right py-2.5 px-3">Chg%</th>
              <th className="text-right py-2.5 px-3">Volume</th>
              <th className="text-right py-2.5 px-3">RVOL</th>
              <th className="text-right py-2.5 px-3">RSI</th>
              <th className="text-right py-2.5 px-3">52W</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s, i) => {
              const pct = Number(s.pct_change ?? 0);
              const isUp = pct >= 0;
              return (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 px-3 font-medium">
                    <Link
                      href={`/stock/${s.ticker}`}
                      className="text-blue-400 hover:text-blue-300"
                    >
                      {String(s.ticker)}
                    </Link>
                  </td>
                  <td className="py-2 px-3 text-gray-300 truncate max-w-[180px]">
                    {String(s.name ?? "—")}
                  </td>
                  <td className="py-2 px-3 text-gray-400 text-xs truncate max-w-[150px]">
                    {String(s.industry ?? "—")}
                  </td>
                  <td className="py-2 px-3 text-right text-white font-medium">
                    ${Number(s.close).toFixed(2)}
                  </td>
                  <td className={`py-2 px-3 text-right font-medium ${isUp ? "text-emerald-400" : "text-red-400"}`}>
                    {isUp ? "+" : ""}
                    {pct.toFixed(2)}%
                  </td>
                  <td className="py-2 px-3 text-right text-gray-400">
                    {Number(s.volume).toLocaleString()}
                  </td>
                  <td className="py-2 px-3 text-right text-amber-400">
                    {s.rvol ? `${Number(s.rvol).toFixed(1)}x` : "—"}
                  </td>
                  <td className="py-2 px-3 text-right text-gray-300">
                    {s.rsi14 ? Number(s.rsi14).toFixed(0) : "—"}
                  </td>
                  <td className="py-2 px-3 text-right text-xs">
                    {s.is_52wk_high ? (
                      <span className="text-emerald-400 font-bold">HI</span>
                    ) : s.is_52wk_low ? (
                      <span className="text-red-400 font-bold">LO</span>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-gray-600 text-xs mt-3">
        {stocks.length} stocks in {sectorName}
      </p>
    </div>
  );
}
