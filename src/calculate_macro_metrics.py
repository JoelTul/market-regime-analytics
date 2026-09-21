from pathlib import Path

import pandas as pd


INPUT_PATH = Path("data/raw/fred_macro_data.csv")
OUTPUT_PATH = Path("data/processed/macro_metrics.csv")

EXPECTED_SERIES = [
    "CPIAUCSL",
    "INDPRO",
    "FEDFUNDS",
    "UNRATE",
]


def load_fred_data() -> pd.DataFrame:
    """Load and validate the raw FRED dataset."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "Raw FRED data not found. "
            "Run download_fred_data.py first."
        )

    fred_data = pd.read_csv(
        INPUT_PATH,
        parse_dates=["date"],
    )

    required_columns = {
        "date",
        "series_id",
        "series_name",
        "value",
    }

    missing_columns = required_columns - set(fred_data.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if fred_data.duplicated(["date", "series_id"]).any():
        raise ValueError(
            "Duplicate date and series combinations found."
        )

    missing_series = set(EXPECTED_SERIES) - set(
        fred_data["series_id"].unique()
    )

    if missing_series:
        raise ValueError(
            f"Missing FRED series: {sorted(missing_series)}"
        )

    fred_data["value"] = pd.to_numeric(
        fred_data["value"],
        errors="raise",
    )

    return fred_data


def create_monthly_dataset(
    fred_data: pd.DataFrame,
) -> pd.DataFrame:
    """Reshape FRED observations into one row per month."""

    monthly = fred_data.pivot(
        index="date",
        columns="series_id",
        values="value",
    )

    monthly.columns.name = None

    full_monthly_index = pd.date_range(
        start=monthly.index.min(),
        end=monthly.index.max(),
        freq="MS",
    )

    monthly = monthly.reindex(full_monthly_index)
    monthly.index.name = "date"

    monthly["source_gap"] = (
        monthly[EXPECTED_SERIES]
        .isna()
        .any(axis=1)
    )

    monthly["missing_series"] = (
        monthly[EXPECTED_SERIES]
        .isna()
        .apply(
            lambda row: ",".join(
                row.index[row].tolist()
            ),
            axis=1,
        )
    )

    return monthly.reset_index()


def calculate_macro_metrics(
    monthly: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate inflation, growth, rate, and labor metrics."""

    metrics = monthly.copy()

    metrics["inflation_yoy_pct"] = (
        metrics["CPIAUCSL"]
        .pct_change(
            periods=12,
            fill_method=None,
        )
        * 100
    )

    metrics["industrial_production_yoy_pct"] = (
        metrics["INDPRO"]
        .pct_change(
            periods=12,
            fill_method=None,
        )
        * 100
    )

    metrics["fed_funds_change_12m_pp"] = (
        metrics["FEDFUNDS"].diff(periods=12)
    )

    metrics["unemployment_change_12m_pp"] = (
        metrics["UNRATE"].diff(periods=12)
    )

    metrics = metrics.rename(
        columns={
            "CPIAUCSL": "cpi_index",
            "INDPRO": "industrial_production_index",
            "FEDFUNDS": "fed_funds_rate_pct",
            "UNRATE": "unemployment_rate_pct",
        }
    )

    ordered_columns = [
        "date",
        "cpi_index",
        "inflation_yoy_pct",
        "industrial_production_index",
        "industrial_production_yoy_pct",
        "fed_funds_rate_pct",
        "fed_funds_change_12m_pp",
        "unemployment_rate_pct",
        "unemployment_change_12m_pp",
        "source_gap",
        "missing_series",
    ]

    return metrics[ordered_columns]


def print_summary(metrics: pd.DataFrame) -> None:
    """Print data coverage, gaps, and the latest complete metrics."""

    print(
        f"Date range: "
        f"{metrics['date'].min().date()} to "
        f"{metrics['date'].max().date()}"
    )

    source_gaps = metrics.loc[
        metrics["source_gap"],
        ["date", "missing_series"],
    ]

    print(f"Rows with source gaps: {len(source_gaps)}")

    if not source_gaps.empty:
        print("\nSource-data gaps:")
        print(source_gaps.to_string(index=False))

    metric_columns = [
        "inflation_yoy_pct",
        "industrial_production_yoy_pct",
        "fed_funds_rate_pct",
        "fed_funds_change_12m_pp",
        "unemployment_rate_pct",
        "unemployment_change_12m_pp",
    ]

    complete_metrics = metrics.dropna(
        subset=metric_columns
    )

    if not complete_metrics.empty:
        latest = complete_metrics.iloc[[-1]]

        print("\nLatest complete macroeconomic metrics:")
        
        latest_display = latest[
            ["date", *metric_columns]
        ].copy()

        latest_display["date"] = (
            latest_display["date"]
            .dt.strftime("%Y-%m-%d")
        )

        latest_display[metric_columns] = (
            latest_display[metric_columns].round(2)
        )

        print(
            latest_display.to_string(index=False)
        )


def main() -> None:
    fred_data = load_fred_data()
    monthly = create_monthly_dataset(fred_data)
    metrics = calculate_macro_metrics(monthly)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metrics.to_csv(OUTPUT_PATH, index=False)

    print(
        f"Saved {len(metrics):,} rows to {OUTPUT_PATH}"
    )

    print_summary(metrics)


if __name__ == "__main__":
    main()