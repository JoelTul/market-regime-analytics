from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import pandas as pd
import seaborn as sns


INPUT_PATH = Path(
    "data/processed/regime_performance_summary.csv"
)

OUTPUT_DIR = Path("dashboard/screenshots")

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

REGIME_DISPLAY_NAMES = [
    "Goldilocks",
    "Reflation",
    "Stagflation",
    "Disinflationary\nSlowdown",
]

COLORS = dict(
    zip(
        TICKER_ORDER,
        sns.color_palette(
            "colorblind",
            n_colors=len(TICKER_ORDER),
        ),
    )
)


def load_summary() -> pd.DataFrame:
    """Load and validate the regime-performance summary."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "Regime-performance summary not found. "
            "Run analyze_regime_performance.py first."
        )

    summary = pd.read_csv(INPUT_PATH)

    required_columns = {
        "regime",
        "ticker",
        "asset_name",
        "months",
        "annualized_return_pct",
        "annualized_volatility_pct",
        "positive_months_pct",
    }

    missing_columns = required_columns - set(
        summary.columns
    )

    if missing_columns:
        raise ValueError(
            f"Missing summary columns: "
            f"{sorted(missing_columns)}"
        )

    if summary.duplicated(
        ["regime", "ticker"]
    ).any():
        raise ValueError(
            "Duplicate regime and ticker "
            "combinations found."
        )

    expected_combinations = pd.MultiIndex.from_product(
        [REGIME_ORDER, TICKER_ORDER],
        names=["regime", "ticker"],
    )

    actual_combinations = pd.MultiIndex.from_frame(
        summary[["regime", "ticker"]]
    )

    missing_combinations = (
        expected_combinations.difference(
            actual_combinations
        )
    )

    if len(missing_combinations) > 0:
        raise ValueError(
            "Missing asset-regime combinations: "
            f"{list(missing_combinations)}"
        )

    numeric_columns = [
        "annualized_return_pct",
        "annualized_volatility_pct",
        "positive_months_pct",
    ]

    for column in numeric_columns:
        summary[column] = pd.to_numeric(
            summary[column],
            errors="raise",
        )

    return summary


def create_return_heatmap(
    summary: pd.DataFrame,
) -> None:
    """Create an annotated regime-return heatmap."""

    return_matrix = (
        summary.pivot(
            index="ticker",
            columns="regime",
            values="annualized_return_pct",
        )
        .reindex(
            index=TICKER_ORDER,
            columns=REGIME_ORDER,
        )
    )

    annotations = return_matrix.apply(
        lambda column: column.map(
            lambda value: f"{value:.1f}%"
        )
    )

    color_limit = max(
        abs(return_matrix.min().min()),
        abs(return_matrix.max().max()),
    )

    fig, ax = plt.subplots(
        figsize=(13, 7)
    )

    sns.heatmap(
        return_matrix,
        annot=annotations,
        fmt="",
        cmap="vlag",
        center=0,
        vmin=-color_limit,
        vmax=color_limit,
        linewidths=1,
        linecolor="white",
        cbar_kws={
            "label": "Annualized return",
        },
        ax=ax,
    )

    ax.set_title(
        "Annualized Asset Returns by Economic Regime",
        fontsize=16,
        weight="bold",
        pad=18,
    )

    ax.set_xlabel("")
    ax.set_ylabel("Asset")

    ax.set_xticklabels(
        REGIME_DISPLAY_NAMES,
        rotation=0,
    )

    ax.set_yticklabels(
        ax.get_yticklabels(),
        rotation=0,
    )

    colorbar = ax.collections[0].colorbar

    colorbar.ax.yaxis.set_major_formatter(
        PercentFormatter(
            xmax=100,
            decimals=0,
        )
    )

    fig.text(
        0.5,
        0.015,
        (
            "Geometric annualized returns across "
            "historical months assigned to each regime."
        ),
        ha="center",
        fontsize=9,
        color="dimgray",
    )

    fig.tight_layout(
        rect=[0, 0.04, 1, 1]
    )

    output_path = (
        OUTPUT_DIR
        / "regime_return_heatmap.png"
    )

    fig.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(f"Saved {output_path}")


def create_risk_return_facets(
    summary: pd.DataFrame,
) -> None:
    """Create risk-versus-return panels by regime."""

    x_values = summary[
        "annualized_volatility_pct"
    ]

    y_values = summary[
        "annualized_return_pct"
    ]

    x_padding = max(
        (x_values.max() - x_values.min()) * 0.12,
        1,
    )

    y_padding = max(
        (y_values.max() - y_values.min()) * 0.12,
        2,
    )

    x_min = max(
        0,
        x_values.min() - x_padding,
    )

    x_max = x_values.max() + x_padding
    y_min = y_values.min() - y_padding
    y_max = y_values.max() + y_padding

    label_offsets = {
        "SPY": (7, 7),
        "QQQ": (7, 7),
        "SCHD": (7, -14),
        "IWM": (7, -14),
        "TLT": (7, 7),
        "GLD": (7, -14),
    }

    fig, axes = plt.subplots(
        nrows=2,
        ncols=2,
        figsize=(14, 10),
        sharex=True,
        sharey=True,
    )

    for ax, regime in zip(
        axes.flat,
        REGIME_ORDER,
    ):
        regime_data = summary.loc[
            summary["regime"] == regime
        ]

        for row in regime_data.itertuples():
            ax.scatter(
                row.annualized_volatility_pct,
                row.annualized_return_pct,
                color=COLORS[row.ticker],
                s=130,
                edgecolor="white",
                linewidth=1,
                zorder=3,
            )

            ax.annotate(
                row.ticker,
                (
                    row.annualized_volatility_pct,
                    row.annualized_return_pct,
                ),
                xytext=label_offsets[row.ticker],
                textcoords="offset points",
                weight="bold",
                fontsize=9,
            )

        ax.axhline(
            0,
            color="black",
            linewidth=0.8,
            linestyle="--",
            alpha=0.6,
        )

        ax.set_title(
            regime,
            fontsize=13,
            weight="bold",
        )

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)

        ax.xaxis.set_major_formatter(
            PercentFormatter(
                xmax=100,
                decimals=0,
            )
        )

        ax.yaxis.set_major_formatter(
            PercentFormatter(
                xmax=100,
                decimals=0,
            )
        )

        ax.grid(alpha=0.2)
        sns.despine(ax=ax)

    fig.suptitle(
        "Asset Risk and Return Across Economic Regimes",
        fontsize=17,
        weight="bold",
        y=0.98,
    )

    fig.supxlabel(
        "Annualized volatility",
        fontsize=11,
        y=0.055,
    )

    fig.supylabel(
        "Annualized return",
        fontsize=11,
        x=0.025,
    )

    fig.text(
        0.5,
        0.015,
        (
            "Ex-post descriptive analysis; regime "
            "labels are not real-time trading signals."
        ),
        ha="center",
        fontsize=9,
        color="dimgray",
    )

    fig.tight_layout(
        rect=[0.045, 0.09, 1, 0.95]
    )
    output_path = (
        OUTPUT_DIR
        / "regime_risk_return.png"
    )

    fig.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(f"Saved {output_path}")


def main() -> None:
    sns.set_theme(
        style="whitegrid",
        context="notebook",
    )

    summary = load_summary()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    create_return_heatmap(summary)
    create_risk_return_facets(summary)


if __name__ == "__main__":
    main()