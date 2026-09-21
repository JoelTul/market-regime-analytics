from pathlib import Path

import pandas as pd


INPUT_PATH = Path("data/processed/macro_metrics.csv")
OUTPUT_PATH = Path("data/processed/macro_regimes.csv")

TREND_LOOKBACK_MONTHS = 3
ANALYSIS_START_DATE = pd.Timestamp("2012-01-01")

REGIME_ORDER = [
    "Goldilocks",
    "Reflation",
    "Stagflation",
    "Disinflationary Slowdown",
]


def load_macro_metrics() -> pd.DataFrame:
    """Load and validate the monthly macroeconomic metrics."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "Processed macroeconomic metrics not found. "
            "Run calculate_macro_metrics.py first."
        )

    metrics = pd.read_csv(
        INPUT_PATH,
        parse_dates=["date"],
    )

    required_columns = {
        "date",
        "inflation_yoy_pct",
        "industrial_production_yoy_pct",
        "source_gap",
    }

    missing_columns = required_columns - set(metrics.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if metrics["date"].duplicated().any():
        raise ValueError(
            "Duplicate monthly dates found."
        )

    metrics["source_gap"] = (
        metrics["source_gap"]
        .astype(str)
        .str.lower()
        .eq("true")
    )

    return metrics.sort_values("date").reset_index(drop=True)


def classify_regimes(
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Classify months using inflation and growth directions."""

    regimes = metrics.copy()

    regimes["inflation_trend_3m_pp"] = (
        regimes["inflation_yoy_pct"].diff(
            periods=TREND_LOOKBACK_MONTHS
        )
    )

    regimes["growth_trend_3m_pp"] = (
        regimes["industrial_production_yoy_pct"].diff(
            periods=TREND_LOOKBACK_MONTHS
        )
    )

    valid = (
        regimes["inflation_trend_3m_pp"].notna()
        & regimes["growth_trend_3m_pp"].notna()
        & ~regimes["source_gap"]
    )

    inflation_rising = (
        regimes["inflation_trend_3m_pp"] >= 0
    )

    growth_rising = (
        regimes["growth_trend_3m_pp"] >= 0
    )

    regimes["inflation_direction"] = pd.Series(
        pd.NA,
        index=regimes.index,
        dtype="string",
    )

    regimes["growth_direction"] = pd.Series(
        pd.NA,
        index=regimes.index,
        dtype="string",
    )

    regimes.loc[
        valid & inflation_rising,
        "inflation_direction",
    ] = "Accelerating"

    regimes.loc[
        valid & ~inflation_rising,
        "inflation_direction",
    ] = "Decelerating"

    regimes.loc[
        valid & growth_rising,
        "growth_direction",
    ] = "Accelerating"

    regimes.loc[
        valid & ~growth_rising,
        "growth_direction",
    ] = "Decelerating"

    regimes["regime"] = pd.Series(
        "Insufficient Data",
        index=regimes.index,
        dtype="string",
    )

    regimes.loc[
        valid & growth_rising & ~inflation_rising,
        "regime",
    ] = "Goldilocks"

    regimes.loc[
        valid & growth_rising & inflation_rising,
        "regime",
    ] = "Reflation"

    regimes.loc[
        valid & ~growth_rising & inflation_rising,
        "regime",
    ] = "Stagflation"

    regimes.loc[
        valid & ~growth_rising & ~inflation_rising,
        "regime",
    ] = "Disinflationary Slowdown"

    regimes.loc[
        regimes["source_gap"],
        "regime",
    ] = "Source Data Gap"

    regimes["classification_available"] = valid

    return regimes


def print_summary(regimes: pd.DataFrame) -> None:
    """Print regime distribution and latest classification."""

    analysis_period = regimes.loc[
        regimes["date"] >= ANALYSIS_START_DATE
    ].copy()

    classified = analysis_period.loc[
        analysis_period["classification_available"]
    ]

    counts = (
        classified["regime"]
        .value_counts()
        .reindex(REGIME_ORDER, fill_value=0)
    )

    summary = pd.DataFrame(
        {
            "regime": counts.index,
            "months": counts.values,
        }
    )

    summary["share_pct"] = (
        summary["months"]
        / summary["months"].sum()
        * 100
    ).round(1)

    print(
        f"Analysis period: "
        f"{analysis_period['date'].min().date()} to "
        f"{analysis_period['date'].max().date()}"
    )

    print("\nRegime distribution:")
    print(summary.to_string(index=False))

    unavailable_count = (
        ~analysis_period["classification_available"]
    ).sum()

    print(
        f"\nMonths without a classification: "
        f"{unavailable_count}"
    )

    if not classified.empty:
        latest = classified.iloc[[-1]][
            [
                "date",
                "inflation_yoy_pct",
                "inflation_trend_3m_pp",
                "industrial_production_yoy_pct",
                "growth_trend_3m_pp",
                "regime",
            ]
        ].copy()

        latest["date"] = (
            latest["date"].dt.strftime("%Y-%m-%d")
        )

        numeric_columns = [
            "inflation_yoy_pct",
            "inflation_trend_3m_pp",
            "industrial_production_yoy_pct",
            "growth_trend_3m_pp",
        ]

        latest[numeric_columns] = (
            latest[numeric_columns].round(2)
        )

        print("\nLatest classified month:")
        print(latest.to_string(index=False))


def main() -> None:
    metrics = load_macro_metrics()
    regimes = classify_regimes(metrics)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    regimes.to_csv(OUTPUT_PATH, index=False)

    print(
        f"Saved {len(regimes):,} rows to {OUTPUT_PATH}"
    )

    print_summary(regimes)


if __name__ == "__main__":
    main()