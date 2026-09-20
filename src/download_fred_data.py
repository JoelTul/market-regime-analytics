from pathlib import Path

import pandas as pd
from pandas_datareader import data as web


START_DATE = "2011-01-01"
OUTPUT_PATH = Path("data/raw/fred_macro_data.csv")

FRED_SERIES = {
    "CPIAUCSL": "Consumer Price Index",
    "INDPRO": "Industrial Production Index",
    "FEDFUNDS": "Effective Federal Funds Rate",
    "UNRATE": "Unemployment Rate",
}


def download_fred_data() -> pd.DataFrame:
    """Download monthly macroeconomic series from FRED."""

    end_date = pd.Timestamp.today().normalize()

    fred_data = web.DataReader(
        list(FRED_SERIES),
        "fred",
        START_DATE,
        end_date,
    )

    return fred_data


def reshape_data(fred_data: pd.DataFrame) -> pd.DataFrame:
    """Convert the wide FRED dataset into a tidy long format."""

    macro_data = (
        fred_data.rename_axis("date")
        .reset_index()
        .melt(
            id_vars="date",
            var_name="series_id",
            value_name="value",
        )
        .dropna(subset=["value"])
    )

    macro_data["series_name"] = macro_data["series_id"].map(
        FRED_SERIES
    )

    macro_data = macro_data[
        ["date", "series_id", "series_name", "value"]
    ]

    return macro_data.sort_values(
        ["series_id", "date"]
    ).reset_index(drop=True)


def validate_data(macro_data: pd.DataFrame) -> None:
    """Validate the downloaded macroeconomic dataset."""

    required_columns = {
        "date",
        "series_id",
        "series_name",
        "value",
    }

    missing_columns = required_columns - set(macro_data.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if macro_data.empty:
        raise ValueError("No FRED data was downloaded.")

    if macro_data.duplicated(["date", "series_id"]).any():
        raise ValueError(
            "Duplicate date and series combinations found."
        )

    missing_series = set(FRED_SERIES) - set(
        macro_data["series_id"].unique()
    )

    if missing_series:
        raise ValueError(
            f"Missing FRED series: {sorted(missing_series)}"
        )

    if macro_data["value"].isna().any():
        raise ValueError("Missing macroeconomic values found.")


def print_summary(macro_data: pd.DataFrame) -> None:
    """Print the coverage of each downloaded series."""

    summary = (
        macro_data.groupby(["series_id", "series_name"])
        .agg(
            start_date=("date", "min"),
            end_date=("date", "max"),
            observations=("value", "count"),
        )
        .reset_index()
    )

    print(summary.to_string(index=False))


def main() -> None:
    fred_data = download_fred_data()
    macro_data = reshape_data(fred_data)
    validate_data(macro_data)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    macro_data.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(macro_data):,} rows to {OUTPUT_PATH}")
    print_summary(macro_data)


if __name__ == "__main__":
    main()