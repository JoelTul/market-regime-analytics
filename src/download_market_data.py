from pathlib import Path

import pandas as pd
import yfinance as yf


ASSETS = {
    "SPY": "US Large-Cap Stocks",
    "QQQ": "US Growth Stocks",
    "SCHD": "US Dividend Stocks",
    "IWM": "US Small-Cap Stocks",
    "TLT": "Long-Term US Treasury Bonds",
    "GLD": "Gold",
}

START_DATE = "2012-01-01"
OUTPUT_PATH = Path("data/raw/market_prices.csv")


def download_market_prices() -> pd.DataFrame:
    """Download adjusted daily closing prices and reshape them for analysis."""

    market_data = yf.download(
        tickers=list(ASSETS),
        start=START_DATE,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if market_data.empty:
        raise RuntimeError("No market data was downloaded.")

    closing_prices = market_data["Close"].copy()
    missing_tickers = [
    ticker
    for ticker in ASSETS
    if ticker not in closing_prices.columns
    or closing_prices[ticker].dropna().empty
]

    if missing_tickers:
        raise RuntimeError(
            f"Missing price data for: {', '.join(missing_tickers)}"
        )
    closing_prices.index.name = "date"

    prices_long = (
        closing_prices.reset_index()
        .melt(
            id_vars="date",
            var_name="ticker",
            value_name="adjusted_close",
        )
        .dropna(subset=["adjusted_close"])
        .sort_values(["ticker", "date"])
    )

    prices_long["asset_name"] = prices_long["ticker"].map(ASSETS)

    return prices_long[
        ["date", "ticker", "asset_name", "adjusted_close"]
    ]


def main() -> None:
    prices = download_market_prices()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(OUTPUT_PATH, index=False)

    summary = prices.groupby("ticker").agg(
        first_date=("date", "min"),
        last_date=("date", "max"),
        observations=("date", "count"),
    )

    print(f"Saved {len(prices):,} rows to {OUTPUT_PATH}")
    print(summary)


if __name__ == "__main__":
    main()