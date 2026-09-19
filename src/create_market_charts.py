from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd
import seaborn as sns


INPUT_PATH = Path("data/processed/market_metrics.csv")
OUTPUT_DIR = Path("dashboard/screenshots")
TRADING_DAYS_PER_YEAR = 252

TICKER_ORDER = ["SPY", "QQQ", "SCHD", "IWM", "TLT", "GLD"]

COLORS = dict(
    zip(
        TICKER_ORDER,
        sns.color_palette("colorblind", n_colors=len(TICKER_ORDER)),
    )
)


def load_metrics() -> pd.DataFrame:
    """Load calculated market metrics."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "Processed metrics not found. "
            "Run calculate_market_metrics.py first."
        )

    return pd.read_csv(INPUT_PATH, parse_dates=["date"])


def create_asset_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    """Calculate long-term return and risk statistics for each asset."""

    rows = []

    for ticker, ticker_data in metrics.groupby("ticker"):
        ticker_data = ticker_data.sort_values("date")

        years = (
            ticker_data["date"].iloc[-1]
            - ticker_data["date"].iloc[0]
        ).days / 365.25

        ending_value = ticker_data["growth_of_one"].iloc[-1]

        rows.append(
            {
                "ticker": ticker,
                "cagr": ending_value ** (1 / years) - 1,
                "annualized_volatility": (
                    ticker_data["daily_return"].std()
                    * np.sqrt(TRADING_DAYS_PER_YEAR)
                ),
                "maximum_drawdown": ticker_data["drawdown"].min(),
            }
        )

    return pd.DataFrame(rows)


def create_growth_chart(metrics: pd.DataFrame) -> None:
    """Create a chart showing how $1 grew in each asset."""

    fig, ax = plt.subplots(figsize=(13, 7))

    for ticker in TICKER_ORDER:
        ticker_data = metrics.loc[metrics["ticker"] == ticker]

        ax.plot(
            ticker_data["date"],
            ticker_data["growth_of_one"],
            label=ticker,
            color=COLORS[ticker],
            linewidth=1.4,
        )

    ax.axhline(
        1,
        color="black",
        linewidth=0.8,
        linestyle="--",
        alpha=0.6,
    )

    ax.set_title(
        "Growth of $1 Invested Since 2012",
        fontsize=16,
        weight="bold",
    )
    ax.set_xlabel("")
    ax.set_ylabel("Value of initial $1 investment")
    ax.legend(
        title="Asset",
        ncol=3,
        frameon=False,
    )
    ax.grid(alpha=0.2)
    sns.despine()

    fig.tight_layout()

    output_path = OUTPUT_DIR / "growth_of_one.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved {output_path}")


def create_risk_return_chart(summary: pd.DataFrame) -> None:
    """Compare annualized return and volatility."""

    fig, ax = plt.subplots(figsize=(10, 7))

    label_offsets = {
        "SPY": (7, 7),
        "QQQ": (7, 7),
        "SCHD": (7, -14),
        "IWM": (7, -14),
        "TLT": (7, 7),
        "GLD": (7, 7),
    }

    for row in summary.itertuples():
        ax.scatter(
            row.annualized_volatility,
            row.cagr,
            color=COLORS[row.ticker],
            s=140,
            edgecolor="white",
            linewidth=1,
        )

        ax.annotate(
            row.ticker,
            (row.annualized_volatility, row.cagr),
            xytext=label_offsets[row.ticker],
            textcoords="offset points",
            weight="bold",
        )

    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))

    ax.set_title(
        "Annualized Return vs. Volatility",
        fontsize=16,
        weight="bold",
    )
    ax.set_xlabel("Annualized volatility")
    ax.set_ylabel("Compound annual growth rate")
    ax.grid(alpha=0.2)
    sns.despine()

    fig.tight_layout()

    output_path = OUTPUT_DIR / "risk_return_scatter.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved {output_path}")


def create_drawdown_chart(summary: pd.DataFrame) -> None:
    """Compare each asset's maximum historical drawdown."""

    ordered = summary.sort_values("maximum_drawdown")
    bar_colors = [
        COLORS[ticker]
        for ticker in ordered["ticker"]
    ]

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.barh(
        ordered["ticker"],
        ordered["maximum_drawdown"],
        color=bar_colors,
    )

    ax.bar_label(
        bars,
        labels=[
            f"{value:.1%}"
            for value in ordered["maximum_drawdown"]
        ],
        padding=5,
    )

    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1))
    ax.set_xlim(-0.55, 0.02)
    ax.invert_yaxis()

    ax.set_title(
        "Maximum Drawdown by Asset",
        fontsize=16,
        weight="bold",
    )
    ax.set_xlabel("Maximum decline from a previous peak")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.2)
    sns.despine()

    fig.tight_layout()

    output_path = OUTPUT_DIR / "maximum_drawdown.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved {output_path}")


def main() -> None:
    metrics = load_metrics()
    summary = create_asset_summary(metrics)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    create_growth_chart(metrics)
    create_risk_return_chart(summary)
    create_drawdown_chart(summary)


if __name__ == "__main__":
    main()