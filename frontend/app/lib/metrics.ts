/**
 * METRIC_CATALOG — canonical definition of every market_summary metric.
 *
 * This is the single source of truth for:
 * - Display labels and descriptions
 * - Default chart type for each metric
 * - Category grouping
 * - Color theming
 *
 * Adding a new metric to the dashboard = adding one entry here
 * + one BlockConfig entry in the page layout.
 */

export type ChartType = "LineChart" | "AreaChart" | "BarChart" | "StatCard" | "Table" | "Heatmap";
export type MetricCategory =
  | "breadth"
  | "momentum"
  | "breakout"
  | "index"
  | "volatility"
  | "rsi";

export interface MetricDefinition {
  label: string;
  description: string;
  category: MetricCategory;
  chartType: ChartType;
  color?: string;
  formatAs?: "number" | "percent" | "ratio" | "price";
}

export const METRIC_CATALOG: Record<string, MetricDefinition> = {
  // --- Advance / Decline ---
  adv:        { label: "Advancing",        description: "Stocks closing above prior close",              category: "breadth",   chartType: "AreaChart",  color: "emerald",  formatAs: "number"  },
  dec:        { label: "Declining",         description: "Stocks closing below prior close",             category: "breadth",   chartType: "AreaChart",  color: "red",      formatAs: "number"  },
  rat:        { label: "A/D Ratio (1d)",    description: "Advancing / Declining (1-day)",                category: "breadth",   chartType: "LineChart",  color: "blue",     formatAs: "ratio"   },
  rat5:       { label: "A/D Ratio (5d)",    description: "5-day rolling advance/decline ratio",          category: "breadth",   chartType: "LineChart",  color: "indigo",   formatAs: "ratio"   },
  rat10:      { label: "A/D Ratio (10d)",   description: "10-day rolling advance/decline ratio",         category: "breadth",   chartType: "LineChart",  color: "violet",   formatAs: "ratio"   },
  voladv:     { label: "Advancing Volume",  description: "Total volume in advancing stocks",             category: "breadth",   chartType: "AreaChart",  color: "emerald",  formatAs: "number"  },
  voldec:     { label: "Declining Volume",  description: "Total volume in declining stocks",             category: "breadth",   chartType: "AreaChart",  color: "red",      formatAs: "number"  },
  volrat:     { label: "Vol Ratio (1d)",    description: "Advancing / Declining volume ratio",           category: "breadth",   chartType: "LineChart",  color: "blue",     formatAs: "ratio"   },
  volrat5:    { label: "Vol Ratio (5d)",    description: "5-day rolling volume ratio",                   category: "breadth",   chartType: "LineChart",  color: "indigo",   formatAs: "ratio"   },
  volrat10:   { label: "Vol Ratio (10d)",   description: "10-day rolling volume ratio",                  category: "breadth",   chartType: "LineChart",  color: "violet",   formatAs: "ratio"   },

  // --- McClellan ---
  mcclellan:  { label: "McClellan Oscillator", description: "EMA19 − EMA39 of normalized A/D",          category: "breadth",   chartType: "LineChart",  color: "cyan",     formatAs: "number"  },
  adv_ema19:  { label: "A/D EMA 19",       description: "19-day EMA of normalized advance/decline",     category: "breadth",   chartType: "LineChart",  color: "teal",     formatAs: "number"  },
  adv_ema39:  { label: "A/D EMA 39",       description: "39-day EMA of normalized advance/decline",     category: "breadth",   chartType: "LineChart",  color: "sky",      formatAs: "number"  },

  // --- Moving Average Breadth ---
  a050ma:     { label: "Above SMA 50",     description: "Stocks above 50-day SMA",                      category: "breadth",   chartType: "LineChart",  color: "emerald",  formatAs: "number"  },
  b050ma:     { label: "Below SMA 50",     description: "Stocks below 50-day SMA",                      category: "breadth",   chartType: "LineChart",  color: "red",      formatAs: "number"  },
  a200ma:     { label: "Above SMA 200",    description: "Stocks above 200-day SMA",                     category: "breadth",   chartType: "LineChart",  color: "emerald",  formatAs: "number"  },
  b200ma:     { label: "Below SMA 200",    description: "Stocks below 200-day SMA",                     category: "breadth",   chartType: "LineChart",  color: "red",      formatAs: "number"  },
  pcta200ma:  { label: "% Above SMA 200",  description: "Percentage above 200-day SMA",                 category: "breadth",   chartType: "LineChart",  color: "blue",     formatAs: "percent" },
  t2108:      { label: "T2108 (% >SMA40)", description: "% of stocks above 40-day SMA (Zweig Thrust)",  category: "breadth",   chartType: "LineChart",  color: "purple",   formatAs: "percent" },

  // --- New Highs / Lows ---
  newhi:      { label: "New 52-Week Highs", description: "Stocks at 252-day closing highs",             category: "breadth",   chartType: "LineChart",  color: "emerald",  formatAs: "number"  },
  newlo:      { label: "New 52-Week Lows",  description: "Stocks at 252-day closing lows",              category: "breadth",   chartType: "LineChart",  color: "red",      formatAs: "number"  },
  newhi010ma: { label: "New Highs 10d MA",  description: "10-day MA of new 52-week highs",              category: "breadth",   chartType: "LineChart",  color: "emerald",  formatAs: "number"  },
  newlo010ma: { label: "New Lows 10d MA",   description: "10-day MA of new 52-week lows",               category: "breadth",   chartType: "LineChart",  color: "red",      formatAs: "number"  },
  pctnewhi:   { label: "% New Highs",       description: "New highs as % of universe",                  category: "breadth",   chartType: "LineChart",  color: "emerald",  formatAs: "percent" },
  pctnewlo:   { label: "% New Lows",        description: "New lows as % of universe",                   category: "breadth",   chartType: "LineChart",  color: "red",      formatAs: "percent" },

  // --- Extreme Candles ---
  extremeup:  { label: "Extreme Up Days",   description: "Strong bullish candles exceeding ATR21",      category: "momentum",  chartType: "BarChart",   color: "emerald",  formatAs: "number"  },
  extremedn:  { label: "Extreme Down Days", description: "Strong bearish candles exceeding ATR21",      category: "momentum",  chartType: "BarChart",   color: "red",      formatAs: "number"  },

  // --- Momentum Movers ---
  up4:        { label: "Up 4%+ Count",      description: "Stocks up 4%+ on elevated volume",            category: "momentum",  chartType: "BarChart",   color: "emerald",  formatAs: "number"  },
  dn4:        { label: "Down 4%+ Count",    description: "Stocks down 4%+ on elevated volume",          category: "momentum",  chartType: "BarChart",   color: "red",      formatAs: "number"  },
  up25q:      { label: "Up 25%+ Quarterly", description: "Stocks up 25%+ from 65-day low (liq filtered)", category: "momentum", chartType: "StatCard",  color: "emerald",  formatAs: "number"  },
  dn25q:      { label: "Down 25%+ Quarterly", description: "Stocks down 25%+ from 65-day high",         category: "momentum",  chartType: "StatCard",   color: "red",      formatAs: "number"  },
  up25m:      { label: "Up 25%+ Monthly",   description: "Stocks up 25%+ vs 20-day close",              category: "momentum",  chartType: "StatCard",   color: "emerald",  formatAs: "number"  },
  dn25m:      { label: "Down 25%+ Monthly", description: "Stocks down 25%+ vs 20-day close",            category: "momentum",  chartType: "StatCard",   color: "red",      formatAs: "number"  },
  up50m:      { label: "Up 50%+ Monthly",   description: "Stocks up 50%+ vs 20-day close",              category: "momentum",  chartType: "StatCard",   color: "emerald",  formatAs: "number"  },
  dn50m:      { label: "Down 50%+ Monthly", description: "Stocks down 50%+ vs 20-day close",            category: "momentum",  chartType: "StatCard",   color: "red",      formatAs: "number"  },
  up1334:     { label: "Up 13%+ / 34d",     description: "Stocks up 13%+ from 34-day low",              category: "momentum",  chartType: "StatCard",   color: "emerald",  formatAs: "number"  },
  dn1334:     { label: "Down 13%+ / 34d",   description: "Stocks down 13%+ from 34-day high",           category: "momentum",  chartType: "StatCard",   color: "red",      formatAs: "number"  },

  // --- RSI Breadth ---
  rsios:      { label: "RSI Oversold",      description: "Stocks with RSI(14) < 30",                    category: "rsi",       chartType: "LineChart",  color: "emerald",  formatAs: "number"  },
  rsiob:      { label: "RSI Overbought",    description: "Stocks with RSI(14) > 70",                    category: "rsi",       chartType: "LineChart",  color: "red",      formatAs: "number"  },
  ratrsios:   { label: "% Oversold",        description: "Oversold as % of universe",                   category: "rsi",       chartType: "StatCard",   color: "emerald",  formatAs: "percent" },
  ratrsiob:   { label: "% Overbought",      description: "Overbought as % of universe",                 category: "rsi",       chartType: "StatCard",   color: "red",      formatAs: "percent" },

  // --- Breakout Quality ---
  ratbu021:   { label: "Breakout Ratio 21d", description: "Confirmed / failed 21-day breakouts",        category: "breakout",  chartType: "StatCard",   color: "blue",     formatAs: "ratio"   },
  ratbd021:   { label: "Breakdown Ratio 21d", description: "Confirmed / failed 21-day breakdowns",      category: "breakout",  chartType: "StatCard",   color: "orange",   formatAs: "ratio"   },
  ratbu063:   { label: "Breakout Ratio 63d",  description: "Confirmed / failed 63-day breakouts",       category: "breakout",  chartType: "StatCard",   color: "blue",     formatAs: "ratio"   },
  ratbd063:   { label: "Breakdown Ratio 63d",  description: "Confirmed / failed 63-day breakdowns",     category: "breakout",  chartType: "StatCard",   color: "orange",   formatAs: "ratio"   },
  ratbu252:   { label: "Breakout Ratio 252d", description: "Confirmed / failed 252-day breakouts",      category: "breakout",  chartType: "StatCard",   color: "blue",     formatAs: "ratio"   },
  ratbd252:   { label: "Breakdown Ratio 252d", description: "Confirmed / failed 252-day breakdowns",    category: "breakout",  chartType: "StatCard",   color: "orange",   formatAs: "ratio"   },

  // --- Index Overlays ---
  spx:        { label: "S&P 500",           description: "S&P 500 index close",                         category: "index",     chartType: "LineChart",  color: "blue",     formatAs: "price"   },
  spxrsi:     { label: "SPX RSI(14)",        description: "S&P 500 RSI 14-day",                         category: "index",     chartType: "LineChart",  color: "indigo",   formatAs: "number"  },
  ndx:        { label: "Nasdaq 100",         description: "Nasdaq 100 index close",                      category: "index",     chartType: "LineChart",  color: "violet",   formatAs: "price"   },
  ndxrsi:     { label: "NDX RSI(14)",        description: "Nasdaq 100 RSI 14-day",                      category: "index",     chartType: "LineChart",  color: "purple",   formatAs: "number"  },
  vix:        { label: "VIX",               description: "CBOE Volatility Index close",                  category: "volatility", chartType: "LineChart", color: "amber",   formatAs: "number"  },
  spx050ma:   { label: "SPX SMA 50",         description: "S&P 500 50-day simple moving average",       category: "index",     chartType: "LineChart",  color: "sky",      formatAs: "price"   },
  spx200ma:   { label: "SPX SMA 200",        description: "S&P 500 200-day simple moving average",      category: "index",     chartType: "LineChart",  color: "cyan",     formatAs: "price"   },
  ndx050ma:   { label: "NDX SMA 50",         description: "Nasdaq 100 50-day simple moving average",    category: "index",     chartType: "LineChart",  color: "fuchsia",  formatAs: "price"   },
  ndx200ma:   { label: "NDX SMA 200",        description: "Nasdaq 100 200-day simple moving average",   category: "index",     chartType: "LineChart",  color: "pink",     formatAs: "price"   },
};

export function getMetric(key: string): MetricDefinition | undefined {
  return METRIC_CATALOG[key];
}

export function getMetricsByCategory(category: MetricCategory): Record<string, MetricDefinition> {
  return Object.fromEntries(
    Object.entries(METRIC_CATALOG).filter(([, v]) => v.category === category)
  );
}
