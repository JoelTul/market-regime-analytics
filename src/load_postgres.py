from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


REGIME_INPUT_PATH = Path(
    "data/processed/macro_regimes.csv"
)

PERFORMANCE_INPUT_PATH = Path(
    "data/processed/asset_regime_monthly.csv"
)

REQUIRED_ENVIRONMENT_VARIABLES = [
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
]


def create_database_engine():
    """Create a PostgreSQL connection from environment variables."""

    load_dotenv()

    missing_variables = [
        variable
        for variable in REQUIRED_ENVIRONMENT_VARIABLES
        if not os.getenv(variable)
    ]

    if missing_variables:
        raise ValueError(
            "Missing environment variables: "
            f"{missing_variables}"
        )

    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DB"],
    )

    return create_engine(
        database_url,
        future=True,
    )


def parse_boolean(
    values: pd.Series,
) -> pd.Series:
    """Convert CSV boolean values into Python booleans."""

    parsed = (
        values.astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
            }
        )
    )

    if parsed.isna().any():
        raise ValueError(
            "Invalid boolean value found."
        )

    return parsed


def prepare_for_sql(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Replace pandas missing values with database nulls."""

    return dataframe.astype(object).where(
        pd.notna(dataframe),
        None,
    )


def load_source_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load and transform the generated analytical datasets."""

    if not REGIME_INPUT_PATH.exists():
        raise FileNotFoundError(
            "macro_regimes.csv not found. "
            "Run classify_market_regimes.py first."
        )

    if not PERFORMANCE_INPUT_PATH.exists():
        raise FileNotFoundError(
            "asset_regime_monthly.csv not found. "
            "Run analyze_regime_performance.py first."
        )

    regimes = pd.read_csv(
        REGIME_INPUT_PATH,
        parse_dates=["date"],
    )

    performance = pd.read_csv(
        PERFORMANCE_INPUT_PATH,
        parse_dates=["month"],
    )

    required_regime_columns = {
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
        "inflation_trend_3m_pp",
        "growth_trend_3m_pp",
        "inflation_direction",
        "growth_direction",
        "regime",
        "classification_available",
    }

    missing_regime_columns = (
        required_regime_columns
        - set(regimes.columns)
    )

    if missing_regime_columns:
        raise ValueError(
            "Missing regime columns: "
            f"{sorted(missing_regime_columns)}"
        )

    required_performance_columns = {
        "month",
        "ticker",
        "asset_name",
        "monthly_return",
        "trading_days",
        "month_end_price",
    }

    missing_performance_columns = (
        required_performance_columns
        - set(performance.columns)
    )

    if missing_performance_columns:
        raise ValueError(
            "Missing performance columns: "
            f"{sorted(missing_performance_columns)}"
        )

    regimes["source_gap"] = parse_boolean(
        regimes["source_gap"]
    )

    regimes["classification_available"] = (
        parse_boolean(
            regimes["classification_available"]
        )
    )

    assets = (
        performance[
            ["ticker", "asset_name"]
        ]
        .drop_duplicates()
        .sort_values("ticker")
        .reset_index(drop=True)
    )

    asset_names_per_ticker = (
        assets.groupby("ticker")["asset_name"]
        .nunique()
    )

    if (asset_names_per_ticker > 1).any():
        raise ValueError(
            "A ticker has multiple asset names."
        )

    regimes = regimes.rename(
        columns={"date": "month_date"}
    )

    regimes["month_date"] = (
        regimes["month_date"].dt.date
    )

    regime_columns = [
        "month_date",
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
        "inflation_trend_3m_pp",
        "growth_trend_3m_pp",
        "inflation_direction",
        "growth_direction",
        "regime",
        "classification_available",
    ]

    regimes = regimes[regime_columns]

    performance = performance.rename(
        columns={"month": "month_date"}
    )

    performance["month_date"] = (
        performance["month_date"].dt.date
    )

    performance_columns = [
        "month_date",
        "ticker",
        "monthly_return",
        "trading_days",
        "month_end_price",
    ]

    performance = performance[
        performance_columns
    ]

    return (
        prepare_for_sql(assets),
        prepare_for_sql(regimes),
        prepare_for_sql(performance),
    )


def load_tables(
    engine,
    assets: pd.DataFrame,
    regimes: pd.DataFrame,
    performance: pd.DataFrame,
) -> None:
    """Perform a transactional full refresh of project tables."""

    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM "
                "analytics.asset_monthly_performance"
            )
        )

        connection.execute(
            text(
                "DELETE FROM analytics.macro_regimes"
            )
        )

        connection.execute(
            text(
                "DELETE FROM analytics.assets"
            )
        )

        assets.to_sql(
            name="assets",
            con=connection,
            schema="analytics",
            if_exists="append",
            index=False,
            method="multi",
        )

        regimes.to_sql(
            name="macro_regimes",
            con=connection,
            schema="analytics",
            if_exists="append",
            index=False,
            method="multi",
        )

        performance.to_sql(
            name="asset_monthly_performance",
            con=connection,
            schema="analytics",
            if_exists="append",
            index=False,
            method="multi",
        )


def print_database_counts(engine) -> None:
    """Print row counts from the loaded PostgreSQL tables."""

    count_queries = {
        "assets": (
            "SELECT COUNT(*) "
            "FROM analytics.assets"
        ),
        "macro_regimes": (
            "SELECT COUNT(*) "
            "FROM analytics.macro_regimes"
        ),
        "asset_monthly_performance": (
            "SELECT COUNT(*) "
            "FROM analytics.asset_monthly_performance"
        ),
    }

    print("PostgreSQL row counts:")

    with engine.connect() as connection:
        for table_name, query in count_queries.items():
            row_count = connection.execute(
                text(query)
            ).scalar_one()

            print(
                f"{table_name}: "
                f"{row_count:,}"
            )


def main() -> None:
    engine = create_database_engine()

    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT 1")
            )

        assets, regimes, performance = (
            load_source_data()
        )

        load_tables(
            engine,
            assets,
            regimes,
            performance,
        )

        print_database_counts(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()