from pathlib import Path

import numpy as np
import pandas as pd


INPUT_PATH = Path("data/raw/market_prices.csv")
OUTPUT_PATH = Path("data/processed/market_metrics.csv")
TRADING_DAYS_PER_YEAR = 252


def load_prices() -> pd.DataFrame:
    """Load and validate the raw market-price dataset."""

    prices = pd.read_csv(INPUT_PATH, parse_dates=["date"])

    required_columns = {
        "date",
        "ticker",
        "asset_name",
        "adjusted_close",
    }

    missing_columns = required_columns - set(prices.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if prices.duplicated(["date", "ticker"]).any():
        raise ValueError("Duplicate date and ticker combinations found.")

    if (prices["adjusted_close"] <= 0).any():
        raise ValueError("Adjusted prices must be greater than zero.")

    return prices.sort_values(["ticker", "date"]).reset_index(drop=True)


def calculate_metrics(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate return, volatility, and drawdown metrics."""

    metrics = prices.copy()

    metrics["daily_return"] = (
        metrics.groupby("ticker")["adjusted_close"]
        .pct_change(fill_method=None)
    )

    metrics["growth_of_one"] = (
        metrics["daily_return"]
        .fillna(0)
        .add(1)
        .groupby(metrics["ticker"])
        .cumprod()
    )

    metrics["rolling_21d_volatility"] = (
        metrics.groupby("ticker")["daily_return"]
        .transform(
            lambda returns: (
                returns.rolling(window=21, min_periods=21).std()
                * np.sqrt(TRADING_DAYS_PER_YEAR)
            )
        )
    )

    metrics["rolling_252d_return"] = (
        metrics.groupby("ticker")["adjusted_close"]
        .pct_change(
            periods=TRADING_DAYS_PER_YEAR,
            fill_method=None,
        )
    )

    running_peak = (
        metrics.groupby("ticker")["growth_of_one"]
        .cummax()
    )

    metrics["drawdown"] = (
        metrics["growth_of_one"] / running_peak - 1
    )

    return metrics


def create_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    """Create a high-level performance and risk summary."""

    summary = (
        metrics.groupby(["ticker", "asset_name"])
        .agg(
            total_return=("growth_of_one", lambda values: values.iloc[-1] - 1),
            annualized_volatility=(
                "daily_return",
                lambda values: (
                    values.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
                ),
            ),
            maximum_drawdown=("drawdown", "min"),
        )
        .reset_index()
    )

    percentage_columns = [
        "total_return",
        "annualized_volatility",
        "maximum_drawdown",
    ]

    summary[percentage_columns] = (
        summary[percentage_columns] * 100
    )

    return summary


def main() -> None:
    prices = load_prices()
    metrics = calculate_metrics(prices)
    summary = create_summary(metrics)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(metrics):,} rows to {OUTPUT_PATH}")
    print(summary.round(2).to_string(index=False))


if __name__ == "__main__":
    main()