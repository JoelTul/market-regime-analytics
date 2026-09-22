CREATE SCHEMA IF NOT EXISTS analytics;


CREATE TABLE IF NOT EXISTS analytics.assets (
    ticker VARCHAR(10) PRIMARY KEY,
    asset_name VARCHAR(100) NOT NULL,
    CONSTRAINT assets_ticker_uppercase
        CHECK (ticker = UPPER(ticker))
);


CREATE TABLE IF NOT EXISTS analytics.macro_regimes (
    month_date DATE PRIMARY KEY,

    cpi_index NUMERIC,
    inflation_yoy_pct NUMERIC,

    industrial_production_index NUMERIC,
    industrial_production_yoy_pct NUMERIC,

    fed_funds_rate_pct NUMERIC,
    fed_funds_change_12m_pp NUMERIC,

    unemployment_rate_pct NUMERIC,
    unemployment_change_12m_pp NUMERIC,

    source_gap BOOLEAN NOT NULL,
    missing_series TEXT,

    inflation_trend_3m_pp NUMERIC,
    growth_trend_3m_pp NUMERIC,

    inflation_direction VARCHAR(20),
    growth_direction VARCHAR(20),

    regime VARCHAR(40) NOT NULL,
    classification_available BOOLEAN NOT NULL,

    CONSTRAINT macro_month_first_day
        CHECK (
            EXTRACT(DAY FROM month_date) = 1
        ),

    CONSTRAINT valid_inflation_direction
        CHECK (
            inflation_direction IS NULL
            OR inflation_direction IN (
                'Accelerating',
                'Decelerating'
            )
        ),

    CONSTRAINT valid_growth_direction
        CHECK (
            growth_direction IS NULL
            OR growth_direction IN (
                'Accelerating',
                'Decelerating'
            )
        ),

    CONSTRAINT valid_regime
        CHECK (
            regime IN (
                'Goldilocks',
                'Reflation',
                'Stagflation',
                'Disinflationary Slowdown',
                'Insufficient Data',
                'Source Data Gap'
            )
        )
);


CREATE TABLE IF NOT EXISTS analytics.asset_monthly_performance (
    month_date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,

    monthly_return NUMERIC NOT NULL,
    trading_days INTEGER NOT NULL,
    month_end_price NUMERIC NOT NULL,

    PRIMARY KEY (month_date, ticker),

    CONSTRAINT asset_month_ticker_fk
        FOREIGN KEY (ticker)
        REFERENCES analytics.assets(ticker),

    CONSTRAINT asset_month_regime_fk
        FOREIGN KEY (month_date)
        REFERENCES analytics.macro_regimes(month_date),

    CONSTRAINT asset_month_first_day
        CHECK (
            EXTRACT(DAY FROM month_date) = 1
        ),

    CONSTRAINT valid_monthly_return
        CHECK (monthly_return > -1),

    CONSTRAINT valid_trading_days
        CHECK (
            trading_days BETWEEN 1 AND 31
        ),

    CONSTRAINT positive_month_end_price
        CHECK (month_end_price > 0)
);


CREATE INDEX IF NOT EXISTS idx_macro_regimes_regime
    ON analytics.macro_regimes(regime);


CREATE INDEX IF NOT EXISTS idx_asset_performance_ticker
    ON analytics.asset_monthly_performance(ticker);


CREATE INDEX IF NOT EXISTS idx_asset_performance_month
    ON analytics.asset_monthly_performance(month_date);


COMMENT ON SCHEMA analytics IS
    'Market regime analytics tables and views';


COMMENT ON TABLE analytics.assets IS
    'Reference table containing the analyzed assets';


COMMENT ON TABLE analytics.macro_regimes IS
    'Monthly macroeconomic metrics and regime classifications';


COMMENT ON TABLE analytics.asset_monthly_performance IS
    'Monthly asset returns linked to macroeconomic regimes';