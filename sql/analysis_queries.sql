/*
Market Regime Analytics
Portfolio SQL analysis examples
*/


/* 1. Return and risk-adjusted leaders by regime */

SELECT
    regime,
    ticker,
    annualized_return_pct,
    annualized_volatility_pct,
    return_volatility_ratio,
    return_rank,
    risk_adjusted_rank

FROM analytics.vw_regime_rankings

WHERE
    return_rank = 1
    OR risk_adjusted_rank = 1

ORDER BY
    CASE regime
        WHEN 'Goldilocks' THEN 1
        WHEN 'Reflation' THEN 2
        WHEN 'Stagflation' THEN 3
        WHEN 'Disinflationary Slowdown' THEN 4
    END,
    return_rank;


/* 2. Pivot asset returns across regimes */

SELECT
    ticker,
    asset_name,

    MAX(annualized_return_pct)
        FILTER (
            WHERE regime = 'Goldilocks'
        ) AS goldilocks_return_pct,

    MAX(annualized_return_pct)
        FILTER (
            WHERE regime = 'Reflation'
        ) AS reflation_return_pct,

    MAX(annualized_return_pct)
        FILTER (
            WHERE regime = 'Stagflation'
        ) AS stagflation_return_pct,

    MAX(annualized_return_pct)
        FILTER (
            WHERE regime =
                'Disinflationary Slowdown'
        ) AS slowdown_return_pct

FROM analytics.vw_regime_performance_summary

GROUP BY
    ticker,
    asset_name

ORDER BY
    goldilocks_return_pct DESC;


/* 3. Best and worst asset within each regime */

WITH ranked_assets AS (
    SELECT
        regime,
        ticker,
        annualized_return_pct,

        ROW_NUMBER() OVER (
            PARTITION BY regime
            ORDER BY annualized_return_pct DESC
        ) AS best_rank,

        ROW_NUMBER() OVER (
            PARTITION BY regime
            ORDER BY annualized_return_pct
        ) AS worst_rank

    FROM analytics.vw_regime_performance_summary
)

SELECT
    regime,

    MAX(ticker)
        FILTER (
            WHERE best_rank = 1
        ) AS best_asset,

    MAX(annualized_return_pct)
        FILTER (
            WHERE best_rank = 1
        ) AS best_return_pct,

    MAX(ticker)
        FILTER (
            WHERE worst_rank = 1
        ) AS worst_asset,

    MAX(annualized_return_pct)
        FILTER (
            WHERE worst_rank = 1
        ) AS worst_return_pct,

    ROUND(
        MAX(annualized_return_pct)
            FILTER (
                WHERE best_rank = 1
            )
        -
        MAX(annualized_return_pct)
            FILTER (
                WHERE worst_rank = 1
            ),
        2
    ) AS performance_spread_pct

FROM ranked_assets

GROUP BY regime

ORDER BY performance_spread_pct DESC;


/* 4. Most common month-to-month regime transitions */

WITH ordered_regimes AS (
    SELECT
        month_date,
        regime,

        LAG(month_date) OVER (
            ORDER BY month_date
        ) AS previous_month,

        LAG(regime) OVER (
            ORDER BY month_date
        ) AS previous_regime

    FROM analytics.macro_regimes

    WHERE
        classification_available = TRUE
        AND month_date >= DATE '2012-01-01'
),

transitions AS (
    SELECT
        previous_regime,
        regime AS current_regime

    FROM ordered_regimes

    WHERE
        previous_month IS NOT NULL
        AND month_date = (
            previous_month
            + INTERVAL '1 month'
        )::DATE
)

SELECT
    previous_regime,
    current_regime,
    COUNT(*) AS transition_count

FROM transitions

GROUP BY
    previous_regime,
    current_regime

ORDER BY
    transition_count DESC,
    previous_regime,
    current_regime;


/* 5. Longest continuous regime periods */

WITH ordered_regimes AS (
    SELECT
        month_date,
        regime,

        LAG(month_date) OVER (
            ORDER BY month_date
        ) AS previous_month,

        LAG(regime) OVER (
            ORDER BY month_date
        ) AS previous_regime

    FROM analytics.macro_regimes

    WHERE
        classification_available = TRUE
        AND month_date >= DATE '2012-01-01'
),

sequence_boundaries AS (
    SELECT
        month_date,
        regime,

        CASE
            WHEN regime = previous_regime
                AND month_date = (
                    previous_month
                    + INTERVAL '1 month'
                )::DATE
            THEN 0
            ELSE 1
        END AS starts_new_sequence

    FROM ordered_regimes
),

regime_sequences AS (
    SELECT
        month_date,
        regime,

        SUM(starts_new_sequence) OVER (
            ORDER BY month_date
        ) AS sequence_id

    FROM sequence_boundaries
)

SELECT
    regime,
    MIN(month_date) AS start_month,
    MAX(month_date) AS end_month,
    COUNT(*) AS consecutive_months

FROM regime_sequences

GROUP BY
    regime,
    sequence_id

ORDER BY
    consecutive_months DESC,
    start_month

LIMIT 15;


/* 6. Each regime's effect relative to an asset's average */

WITH asset_average_returns AS (
    SELECT
        ticker,
        AVG(annualized_return_pct)
            AS average_regime_return_pct

    FROM analytics.vw_regime_performance_summary

    GROUP BY ticker
)

SELECT
    summary.ticker,
    summary.regime,
    summary.annualized_return_pct,

    ROUND(
        averages.average_regime_return_pct,
        2
    ) AS average_regime_return_pct,

    ROUND(
        summary.annualized_return_pct
        - averages.average_regime_return_pct,
        2
    ) AS difference_from_asset_average_pct

FROM analytics.vw_regime_performance_summary
    AS summary

INNER JOIN asset_average_returns AS averages
    ON summary.ticker = averages.ticker

ORDER BY
    summary.ticker,
    difference_from_asset_average_pct DESC;