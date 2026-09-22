CREATE OR REPLACE VIEW analytics.vw_asset_regime_monthly AS
SELECT
    performance.month_date,
    performance.ticker,
    assets.asset_name,
    performance.monthly_return,
    performance.monthly_return * 100
        AS monthly_return_pct,
    performance.trading_days,
    performance.month_end_price,

    regimes.regime,
    regimes.inflation_yoy_pct,
    regimes.inflation_trend_3m_pp,
    regimes.industrial_production_yoy_pct,
    regimes.growth_trend_3m_pp,
    regimes.fed_funds_rate_pct,
    regimes.unemployment_rate_pct

FROM analytics.asset_monthly_performance
    AS performance

INNER JOIN analytics.assets AS assets
    ON performance.ticker = assets.ticker

INNER JOIN analytics.macro_regimes AS regimes
    ON performance.month_date = regimes.month_date

WHERE regimes.classification_available = TRUE;


CREATE OR REPLACE VIEW
analytics.vw_regime_performance_summary AS
SELECT
    regime,
    ticker,
    asset_name,
    COUNT(*) AS months,

    ROUND(
        AVG(monthly_return) * 100,
        4
    ) AS average_monthly_return_pct,

    ROUND(
        (
            PERCENTILE_CONT(0.5)
            WITHIN GROUP (
                ORDER BY monthly_return
            )
            * 100
        )::NUMERIC,
        4
    ) AS median_monthly_return_pct,

    ROUND(
        (
            EXP(
                SUM(
                    LN(1 + monthly_return)
                )
                * 12.0
                / COUNT(*)
            )
            - 1
        )
        * 100,
        4
    ) AS annualized_return_pct,

    ROUND(
        STDDEV_SAMP(monthly_return)
        * SQRT(12.0)
        * 100,
        4
    ) AS annualized_volatility_pct,

    ROUND(
        AVG(
            CASE
                WHEN monthly_return > 0
                    THEN 100.0
                ELSE 0.0
            END
        ),
        2
    ) AS positive_months_pct,

    ROUND(
        MAX(monthly_return) * 100,
        4
    ) AS best_month_pct,

    ROUND(
        MIN(monthly_return) * 100,
        4
    ) AS worst_month_pct

FROM analytics.vw_asset_regime_monthly

GROUP BY
    regime,
    ticker,
    asset_name;


CREATE OR REPLACE VIEW
analytics.vw_regime_rankings AS
SELECT
    summary.*,

    RANK() OVER (
        PARTITION BY regime
        ORDER BY annualized_return_pct DESC
    ) AS return_rank,

    RANK() OVER (
        PARTITION BY regime
        ORDER BY
            (
                annualized_return_pct
                / NULLIF(
                    annualized_volatility_pct,
                    0
                )
            ) DESC
    ) AS risk_adjusted_rank,

    ROUND(
        annualized_return_pct
        / NULLIF(
            annualized_volatility_pct,
            0
        ),
        4
    ) AS return_volatility_ratio

FROM analytics.vw_regime_performance_summary
    AS summary;


CREATE OR REPLACE VIEW
analytics.vw_latest_macro_conditions AS
SELECT
    month_date,
    inflation_yoy_pct,
    inflation_trend_3m_pp,
    industrial_production_yoy_pct,
    growth_trend_3m_pp,
    fed_funds_rate_pct,
    unemployment_rate_pct,
    regime

FROM analytics.macro_regimes

WHERE classification_available = TRUE

ORDER BY month_date DESC

LIMIT 1;


COMMENT ON VIEW
analytics.vw_asset_regime_monthly IS
    'Monthly asset performance joined to economic regimes';


COMMENT ON VIEW
analytics.vw_regime_performance_summary IS
    'SQL-calculated asset performance metrics by regime';


COMMENT ON VIEW
analytics.vw_regime_rankings IS
    'Asset rankings within each regime by return and risk-adjusted return';


COMMENT ON VIEW
analytics.vw_latest_macro_conditions IS
    'Most recent classified macroeconomic conditions';


GRANT SELECT ON
    analytics.vw_asset_regime_monthly,
    analytics.vw_regime_performance_summary,
    analytics.vw_regime_rankings,
    analytics.vw_latest_macro_conditions
TO market_analyst;