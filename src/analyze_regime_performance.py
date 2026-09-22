"""Analyze historical asset performance across economic regimes.

This is an ex-post descriptive analysis. Economic indicators are
published after the periods they measure, so the regime labels should
not be interpreted as real-time trading signals.
"""

from pathlib import Path

import numpy as np
import pandas as pd


MARKET_INPUT_PATH = Path(
    "data/processed/market_metrics.csv"
)

REGIME_INPUT_PATH = Path(
    "data/processed/macro_regimes.csv"
)

MONTHLY_OUTPUT_PATH = Path(
    "data/processed/asset_regime_monthly.csv"
)

SUMMARY_OUTPUT_PATH = Path(
    "data/processed/regime_performance_summary.csv"
)

MONTHS_PER_YEAR = 12

TICKER_ORDER = [
    "SPY",
    "QQQ",
    "SCHD",
    "IWM",
    "TLT",
    "GLD",
]

REGIME_ORDER = [
    "Goldilocks",
    "Reflation",
    "Stagflation",
    "Disinflationary Slowdown",
]


def load_market_data() -> pd.DataFrame:
    """Load and validate daily market metrics."""

    if not MARKET_INPUT_PATH.exists():
        raise FileNotFoundError(
            "Market metrics not found. "
            "Run calculate_market_metrics.py first."
        )

    market = pd.read_csv(
        MARKET_INPUT_PATH,
        parse_dates=["date"],
    )

    required_columns = {
        "date",
        "ticker",
        "asset_name",
        "adjusted_close",
        "daily_return",
    }

    missing_columns = required_columns - set(
        market.columns
    )

    if missing_columns:
        raise ValueError(
            f"Missing market columns: "
            f"{sorted(missing_columns)}"
        )

    if market.duplicated(["date", "ticker"]).any():
        raise ValueError(
            "Duplicate market date and ticker "
            "combinations found."
        )

    market["adjusted_close"] = pd.to_numeric(
        market["adjusted_close"],
        errors="raise",
    )

    market["daily_return"] = pd.to_numeric(
        market["daily_return"],
        errors="raise",
    )

    return market.sort_values(
        ["ticker", "date"]
    ).reset_index(drop=True)


def load_regime_data() -> pd.DataFrame:
    """Load and validate monthly regime classifications."""

    if not REGIME_INPUT_PATH.exists():
        raise FileNotFoundError(
            "Regime classifications not found. "
            "Run classify_market_regimes.py first."
        )

    regimes = pd.read_csv(
        REGIME_INPUT_PATH,
        parse_dates=["date"],
    )

    required_columns = {
        "date",
        "regime",
        "classification_available",
        "inflation_yoy_pct",
        "inflation_trend_3m_pp",
        "industrial_production_yoy_pct",
        "growth_trend_3m_pp",
        "fed_funds_rate_pct",
        "unemployment_rate_pct",
    }

    missing_columns = required_columns - set(
        regimes.columns
    )

    if missing_columns:
        raise ValueError(
            f"Missing regime columns: "
            f"{sorted(missing_columns)}"
        )

    if regimes["date"].duplicated().any():
        raise ValueError(
            "Duplicate regime dates found."
        )

    regimes["classification_available"] = (
        regimes["classification_available"]
        .astype(str)
        .str.lower()
        .eq("true")
    )

    regimes["month"] = (
        regimes["date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    return regimes.sort_values(
        "month"
    ).reset_index(drop=True)


def compound_monthly_return(
    returns: pd.Series,
) -> float:
    """Compound daily returns into one monthly return."""

    valid_returns = returns.dropna()

    if valid_returns.empty:
        return np.nan

    return (1 + valid_returns).prod() - 1


def create_monthly_returns(
    market: pd.DataFrame,
) -> pd.DataFrame:
    """Convert daily asset data into monthly returns."""

    monthly_source = market.copy()

    monthly_source["month"] = (
        monthly_source["date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    monthly = (
        monthly_source.groupby(
            ["month", "ticker", "asset_name"],
            as_index=False,
        )
        .agg(
            monthly_return=(
                "daily_return",
                compound_monthly_return,
            ),
            trading_days=(
                "daily_return",
                "count",
            ),
            month_end_price=(
                "adjusted_close",
                "last",
            ),
        )
    )

    if monthly["monthly_return"].isna().any():
        raise ValueError(
            "Missing monthly returns found."
        )

    if (monthly["monthly_return"] <= -1).any():
        raise ValueError(
            "Monthly returns cannot be less "
            "than or equal to -100%."
        )

    return monthly


def merge_with_regimes(
    monthly: pd.DataFrame,
    regimes: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge monthly asset returns with economic regimes."""

    regime_columns = [
        "month",
        "regime",
        "classification_available",
        "inflation_yoy_pct",
        "inflation_trend_3m_pp",
        "industrial_production_yoy_pct",
        "growth_trend_3m_pp",
        "fed_funds_rate_pct",
        "unemployment_rate_pct",
    ]

    merged = monthly.merge(
        regimes[regime_columns],
        on="month",
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    merged["analysis_included"] = (
        merged["_merge"].eq("both")
        & merged["classification_available"].eq(True)
    )

    excluded_months = (
        merged.loc[
            ~merged["analysis_included"],
            ["month", "regime", "_merge"],
        ]
        .drop_duplicates(subset=["month"])
        .sort_values("month")
        .reset_index(drop=True)
    )

    excluded_months["reason"] = np.where(
        excluded_months["_merge"].eq("left_only"),
        "No macro regime available",
        excluded_months["regime"].fillna(
            "Classification unavailable"
        ),
    )

    classified = (
        merged.loc[merged["analysis_included"]]
        .drop(
            columns=[
                "_merge",
                "analysis_included",
            ]
        )
        .sort_values(
            ["month", "ticker"]
        )
        .reset_index(drop=True)
    )

    return classified, excluded_months


def validate_merged_data(
    classified: pd.DataFrame,
) -> None:
    """Validate the completed asset-regime dataset."""

    required_complete_columns = [
        "month",
        "ticker",
        "monthly_return",
        "regime",
        "inflation_yoy_pct",
        "industrial_production_yoy_pct",
    ]

    if (
        classified[required_complete_columns]
        .isna()
        .any()
        .any()
    ):
        raise ValueError(
            "Missing values found in classified data."
        )

    missing_regimes = set(REGIME_ORDER) - set(
        classified["regime"].unique()
    )

    if missing_regimes:
        raise ValueError(
            f"Missing regimes from merged data: "
            f"{sorted(missing_regimes)}"
        )

    months_by_ticker = (
        classified.groupby("ticker")["month"]
        .nunique()
    )

    if months_by_ticker.nunique() != 1:
        raise ValueError(
            "Assets do not have equal classified "
            "monthly coverage."
        )


def create_performance_summary(
    classified: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate asset performance within each regime."""

    rows = []

    grouped = classified.groupby(
        ["regime", "ticker", "asset_name"],
        sort=False,
    )

    for (
        regime,
        ticker,
        asset_name,
    ), group in grouped:
        returns = group["monthly_return"].dropna()
        months = len(returns)

        compounded_growth = (
            1 + returns
        ).prod()

        annualized_return = (
            compounded_growth
            ** (MONTHS_PER_YEAR / months)
            - 1
        )

        annualized_volatility = (
            returns.std(ddof=1)
            * np.sqrt(MONTHS_PER_YEAR)
        )

        rows.append(
            {
                "regime": regime,
                "ticker": ticker,
                "asset_name": asset_name,
                "months": months,
                "average_monthly_return_pct": (
                    returns.mean() * 100
                ),
                "median_monthly_return_pct": (
                    returns.median() * 100
                ),
                "annualized_return_pct": (
                    annualized_return * 100
                ),
                "annualized_volatility_pct": (
                    annualized_volatility * 100
                ),
                "positive_months_pct": (
                    (returns > 0).mean() * 100
                ),
                "best_month_pct": (
                    returns.max() * 100
                ),
                "worst_month_pct": (
                    returns.min() * 100
                ),
            }
        )

    summary = pd.DataFrame(rows)

    regime_rank = {
        regime: position
        for position, regime in enumerate(REGIME_ORDER)
    }

    ticker_rank = {
        ticker: position
        for position, ticker in enumerate(TICKER_ORDER)
    }

    summary["_regime_order"] = (
        summary["regime"].map(regime_rank)
    )

    summary["_ticker_order"] = (
        summary["ticker"].map(ticker_rank)
    )

    summary = (
        summary.sort_values(
            ["_regime_order", "_ticker_order"]
        )
        .drop(
            columns=[
                "_regime_order",
                "_ticker_order",
            ]
        )
        .reset_index(drop=True)
    )

    return summary


def print_results(
    classified: pd.DataFrame,
    summary: pd.DataFrame,
    excluded_months: pd.DataFrame,
) -> None:
    """Print coverage and key regime results."""

    print(
        f"Classified asset-month rows: "
        f"{len(classified):,}"
    )

    month_regimes = classified[
        ["month", "regime"]
    ].drop_duplicates()

    regime_counts = (
        month_regimes["regime"]
        .value_counts()
        .reindex(REGIME_ORDER, fill_value=0)
    )

    print("\nClassified months by regime:")
    print(regime_counts.to_string())

    if not excluded_months.empty:
        excluded_display = excluded_months[
            ["month", "reason"]
        ].copy()

        excluded_display["month"] = (
            excluded_display["month"]
            .dt.strftime("%Y-%m")
        )

        print("\nExcluded market months:")
        print(
            excluded_display.to_string(
                index=False
            )
        )

    return_table = (
        summary.pivot(
            index="ticker",
            columns="regime",
            values="annualized_return_pct",
        )
        .reindex(
            index=TICKER_ORDER,
            columns=REGIME_ORDER,
        )
        .round(2)
    )

    print(
        "\nAnnualized return by asset "
        "and regime (%):"
    )

    print(return_table.to_string())

    best_indices = (
        summary.groupby("regime")[
            "annualized_return_pct"
        ]
        .idxmax()
    )

    best_assets = summary.loc[
        best_indices,
        [
            "regime",
            "ticker",
            "annualized_return_pct",
        ],
    ].copy()

    best_assets["_order"] = (
        best_assets["regime"].map(
            {
                regime: position
                for position, regime
                in enumerate(REGIME_ORDER)
            }
        )
    )

    best_assets = (
        best_assets.sort_values("_order")
        .drop(columns="_order")
    )

    best_assets["annualized_return_pct"] = (
        best_assets["annualized_return_pct"]
        .round(2)
    )

    print("\nHighest-returning asset by regime:")
    print(best_assets.to_string(index=False))


def main() -> None:
    market = load_market_data()
    regimes = load_regime_data()

    monthly = create_monthly_returns(market)

    classified, excluded_months = (
        merge_with_regimes(
            monthly,
            regimes,
        )
    )

    validate_merged_data(classified)

    summary = create_performance_summary(
        classified
    )

    MONTHLY_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    classified.to_csv(
        MONTHLY_OUTPUT_PATH,
        index=False,
    )

    summary.to_csv(
        SUMMARY_OUTPUT_PATH,
        index=False,
    )

    print(
        f"Saved {len(classified):,} rows to "
        f"{MONTHLY_OUTPUT_PATH}"
    )

    print(
        f"Saved {len(summary):,} rows to "
        f"{SUMMARY_OUTPUT_PATH}"
    )

    print_results(
        classified,
        summary,
        excluded_months,
    )


if __name__ == "__main__":
    main()