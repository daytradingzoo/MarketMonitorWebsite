-- =============================================================================
-- Migration 001: Initial schema
-- =============================================================================

-- ---------------------------------------------------------------------------
-- ROLLING WINDOW TABLES (kept for last 252 trading days only)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS stocks (
    ticker          TEXT        NOT NULL,
    name            TEXT,
    sector          TEXT,
    industry        TEXT,
    market_cap      BIGINT,
    exchange        TEXT,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker)
);

CREATE INDEX IF NOT EXISTS idx_stocks_sector   ON stocks (sector);
CREATE INDEX IF NOT EXISTS idx_stocks_exchange ON stocks (exchange);


CREATE TABLE IF NOT EXISTS daily_bars (
    ticker      TEXT    NOT NULL,
    date        DATE    NOT NULL,
    open        NUMERIC NOT NULL,
    high        NUMERIC NOT NULL,
    low         NUMERIC NOT NULL,
    close       NUMERIC NOT NULL,
    volume      BIGINT  NOT NULL,
    vwap        NUMERIC,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_bars_date ON daily_bars (date);


CREATE TABLE IF NOT EXISTS index_bars (
    ticker      TEXT    NOT NULL,   -- $I:SPX, $I:NDX, $I:VIX
    date        DATE    NOT NULL,
    open        NUMERIC,
    high        NUMERIC,
    low         NUMERIC,
    close       NUMERIC NOT NULL,
    volume      BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_index_bars_date ON index_bars (date);


CREATE TABLE IF NOT EXISTS daily_metrics (
    ticker              TEXT    NOT NULL,
    date                DATE    NOT NULL,
    -- Moving averages
    sma20               NUMERIC,
    sma40               NUMERIC,
    sma50               NUMERIC,
    sma200              NUMERIC,
    -- Liquidity / price filters
    ema_dollar_vol_20   NUMERIC,    -- MA(close × volume, 20)
    liqfilter           BOOLEAN,    -- ema_dollar_vol_20 >= 250000
    pricefilter         BOOLEAN,    -- close[20] >= 5
    -- Momentum indicators
    rsi14               NUMERIC,
    atr14               NUMERIC,
    atr21               NUMERIC,
    ibs                 NUMERIC,    -- (close - low) / (high - low)
    rvol                NUMERIC,    -- volume / rolling_20_avg_volume
    -- High/low lookbacks
    hhv007              NUMERIC,
    hhv021              NUMERIC,
    hhv063              NUMERIC,
    hhv252              NUMERIC,
    llv007              NUMERIC,
    llv021              NUMERIC,
    llv063              NUMERIC,
    llv252              NUMERIC,
    -- Flags
    is_52wk_high        BOOLEAN,
    is_52wk_low         BOOLEAN,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics (date);


-- ---------------------------------------------------------------------------
-- LONG-TERM STORAGE TABLES (kept forever — tiny row counts)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS market_summary (
    date            DATE    NOT NULL,
    universe        TEXT    NOT NULL DEFAULT 'all',  -- all, nyse, nasdaq

    -- Universe count
    stocks          INTEGER,

    -- Advance / decline
    adv             INTEGER,
    dec             INTEGER,
    voladv          BIGINT,
    voldec          BIGINT,

    -- Moving average breadth
    a050ma          INTEGER,
    b050ma          INTEGER,
    a200ma          INTEGER,
    b200ma          INTEGER,
    t2108           INTEGER,    -- stocks above SMA40

    -- New highs / lows
    newhi           INTEGER,
    newlo           INTEGER,
    newhi010ma      NUMERIC,    -- 10-day MA of newhi
    newlo010ma      NUMERIC,    -- 10-day MA of newlo

    -- Extreme candles
    extremeup       INTEGER,
    extremedn       INTEGER,

    -- Momentum movers
    up4             INTEGER,    -- up 4%+ on volume
    dn4             INTEGER,
    up25q           INTEGER,    -- up 25%+ from 65-day low
    dn25q           INTEGER,
    up25m           INTEGER,    -- up 25%+ from 20-day close
    dn25m           INTEGER,
    up50m           INTEGER,    -- up 50%+ from 20-day close
    dn50m           INTEGER,
    up1334          INTEGER,    -- up 13%+ from 34-day low
    dn1334          INTEGER,

    -- RSI breadth
    rsios           INTEGER,    -- RSI < 30
    rsiob           INTEGER,    -- RSI > 70
    ratrsios        NUMERIC,    -- rsios / stocks
    ratrsiob        NUMERIC,

    -- Breakout quality: 21-day
    bu021ok         INTEGER,
    bd021ok         INTEGER,
    bu021nok        INTEGER,
    bd021nok        INTEGER,
    ratbu021        NUMERIC,
    ratbd021        NUMERIC,

    -- Breakout quality: 63-day
    bu063ok         INTEGER,
    bd063ok         INTEGER,
    bu063nok        INTEGER,
    bd063nok        INTEGER,
    ratbu063        NUMERIC,
    ratbd063        NUMERIC,

    -- Breakout quality: 252-day
    bu252ok         INTEGER,
    bd252ok         INTEGER,
    bu252nok        INTEGER,
    bd252nok        INTEGER,
    ratbu252        NUMERIC,
    ratbd252        NUMERIC,

    -- A/D ratios
    rat             NUMERIC,    -- adv / dec
    rat5            NUMERIC,    -- 5-day rolling
    rat10           NUMERIC,    -- 10-day rolling
    volrat          NUMERIC,
    volrat5         NUMERIC,
    volrat10        NUMERIC,

    -- McClellan Oscillator
    adv_ema19       NUMERIC,
    adv_ema39       NUMERIC,
    mcclellan       NUMERIC,

    -- Percentage metrics
    pcta200ma       NUMERIC,
    pctb200ma       NUMERIC,
    pctnewhi        NUMERIC,
    pctnewlo        NUMERIC,

    -- Index overlays (from index_bars)
    spx             NUMERIC,
    spxrsi          NUMERIC,
    ndx             NUMERIC,
    ndxrsi          NUMERIC,
    vix             NUMERIC,

    -- SPX moving averages
    spx005ma        NUMERIC,
    spx010ma        NUMERIC,
    spx020ma        NUMERIC,
    spx050ma        NUMERIC,
    spx200ma        NUMERIC,

    -- NDX moving averages
    ndx005ma        NUMERIC,
    ndx010ma        NUMERIC,
    ndx020ma        NUMERIC,
    ndx050ma        NUMERIC,
    ndx200ma        NUMERIC,

    -- Rate of change
    rocspx005       NUMERIC,
    rocspx010       NUMERIC,
    rocspx020       NUMERIC,
    rocndx005       NUMERIC,
    rocndx010       NUMERIC,
    rocndx020       NUMERIC,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (date, universe)
);

CREATE INDEX IF NOT EXISTS idx_market_summary_date     ON market_summary (date DESC);
CREATE INDEX IF NOT EXISTS idx_market_summary_universe ON market_summary (universe, date DESC);


-- ---------------------------------------------------------------------------
-- PIPELINE AUDIT LOG
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS job_runs (
    id              SERIAL      PRIMARY KEY,
    run_date        DATE        NOT NULL,
    mode            TEXT        NOT NULL DEFAULT 'daily',   -- daily, backfill
    status          TEXT        NOT NULL,                   -- success, failed, skipped
    rows_ingested   INTEGER,
    duration_seconds NUMERIC,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_job_runs_date ON job_runs (run_date DESC);


-- ---------------------------------------------------------------------------
-- REPO REGISTRY (extensible block system)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS repos (
    id              TEXT        NOT NULL,
    label           TEXT        NOT NULL,
    description     TEXT,
    table_name      TEXT        NOT NULL,
    dimension_cols  TEXT[]      NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS repo_columns (
    repo_id         TEXT        NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    column_name     TEXT        NOT NULL,
    label           TEXT        NOT NULL,
    description     TEXT,
    category        TEXT,       -- breadth, momentum, volatility, index, breakout
    chart_type      TEXT,       -- LineChart, AreaChart, BarChart, StatCard, Table
    PRIMARY KEY (repo_id, column_name)
);


-- ---------------------------------------------------------------------------
-- USER DASHBOARDS (future — dashboard builder)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_dashboards (
    id          UUID        NOT NULL DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL,
    blocks      JSONB       NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);


-- ---------------------------------------------------------------------------
-- SQL VIEWS
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_latest_summary AS
    SELECT *
    FROM market_summary
    WHERE universe = 'all'
    ORDER BY date DESC
    LIMIT 1;

CREATE OR REPLACE VIEW v_latest_metrics AS
    SELECT
        dm.*,
        s.name,
        s.sector,
        s.industry,
        s.exchange
    FROM daily_metrics dm
    JOIN stocks s ON s.ticker = dm.ticker
    WHERE dm.date = (SELECT MAX(date) FROM daily_metrics);


-- ---------------------------------------------------------------------------
-- SEED: register the initial market_summary repo in the registry
-- ---------------------------------------------------------------------------

INSERT INTO repos (id, label, description, table_name, dimension_cols)
VALUES
    ('mkt_all',    'All US Stocks',    'NYSE + NASDAQ combined breadth metrics', 'market_summary', '{}'),
    ('mkt_nyse',   'NYSE Stocks',      'NYSE-only breadth metrics',              'market_summary', '{}'),
    ('mkt_nasdaq', 'NASDAQ Stocks',    'NASDAQ-only breadth metrics',            'market_summary', '{}')
ON CONFLICT (id) DO NOTHING;

-- Register key columns for the initial repo (representative set)
INSERT INTO repo_columns (repo_id, column_name, label, description, category, chart_type) VALUES
    ('mkt_all', 'adv',        'Advancing Stocks',          'Count of stocks closing above prior close',        'breadth',   'AreaChart'),
    ('mkt_all', 'dec',        'Declining Stocks',          'Count of stocks closing below prior close',        'breadth',   'AreaChart'),
    ('mkt_all', 'rat',        'A/D Ratio (1-day)',         'Advancing / Declining ratio',                      'breadth',   'LineChart'),
    ('mkt_all', 'rat5',       'A/D Ratio (5-day)',         '5-day rolling advance/decline ratio',              'breadth',   'LineChart'),
    ('mkt_all', 'rat10',      'A/D Ratio (10-day)',        '10-day rolling advance/decline ratio',             'breadth',   'LineChart'),
    ('mkt_all', 'mcclellan',  'McClellan Oscillator',      'EMA19 - EMA39 of normalized A/D',                 'breadth',   'LineChart'),
    ('mkt_all', 'newhi',      'New 52-Week Highs',         'Stocks making new 252-day closing highs',         'breadth',   'LineChart'),
    ('mkt_all', 'newlo',      'New 52-Week Lows',          'Stocks making new 252-day closing lows',          'breadth',   'LineChart'),
    ('mkt_all', 'pcta200ma',  '% Above SMA 200',           'Percentage of stocks above 200-day SMA',          'breadth',   'LineChart'),
    ('mkt_all', 'pctnewhi',   '% New 52-Week Highs',       'New highs as % of universe',                      'breadth',   'LineChart'),
    ('mkt_all', 'pctnewlo',   '% New 52-Week Lows',        'New lows as % of universe',                       'breadth',   'LineChart'),
    ('mkt_all', 't2108',      'T2108 (% Above SMA40)',     'Stocks above 40-day SMA (Zweig Breadth Thrust)',  'breadth',   'LineChart'),
    ('mkt_all', 'extremeup',  'Extreme Up Days',           'Strong bullish candles exceeding ATR21',          'momentum',  'BarChart'),
    ('mkt_all', 'extremedn',  'Extreme Down Days',         'Strong bearish candles exceeding ATR21',          'momentum',  'BarChart'),
    ('mkt_all', 'up4',        'Up 4%+ Stocks',             'Stocks up 4%+ on elevated volume',                'momentum',  'BarChart'),
    ('mkt_all', 'dn4',        'Down 4%+ Stocks',           'Stocks down 4%+ on elevated volume',              'momentum',  'BarChart'),
    ('mkt_all', 'up25m',      'Up 25%+ Monthly',           'Stocks up 25%+ vs 20-day close (liq filtered)',   'momentum',  'StatCard'),
    ('mkt_all', 'dn25m',      'Down 25%+ Monthly',         'Stocks down 25%+ vs 20-day close',               'momentum',  'StatCard'),
    ('mkt_all', 'ratbu021',   'Breakout Ratio 21-Day',     'Confirmed / failed breakouts (21-day)',            'breakout',  'StatCard'),
    ('mkt_all', 'ratbu063',   'Breakout Ratio 63-Day',     'Confirmed / failed breakouts (63-day)',            'breakout',  'StatCard'),
    ('mkt_all', 'ratbu252',   'Breakout Ratio 252-Day',    'Confirmed / failed breakouts (252-day)',           'breakout',  'StatCard'),
    ('mkt_all', 'rsios',      'RSI Oversold Count',        'Stocks with RSI(14) < 30',                        'momentum',  'StatCard'),
    ('mkt_all', 'rsiob',      'RSI Overbought Count',      'Stocks with RSI(14) > 70',                        'momentum',  'StatCard'),
    ('mkt_all', 'vix',        'VIX',                       'CBOE Volatility Index close',                     'index',     'LineChart'),
    ('mkt_all', 'spx',        'S&P 500',                   'S&P 500 index close',                             'index',     'LineChart'),
    ('mkt_all', 'ndx',        'Nasdaq 100',                'Nasdaq 100 index close',                          'index',     'LineChart')
ON CONFLICT (repo_id, column_name) DO NOTHING;
