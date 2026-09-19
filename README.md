# Market Regime Analytics

An end-to-end financial analytics project examining asset performance, risk, and diversification across changing economic environments.

## Overview

This project builds a reproducible analytics pipeline for comparing major asset classes and investment styles.

The current phase downloads adjusted daily market prices, validates the data, calculates performance and risk metrics, and generates portfolio-ready visualizations.

Future phases will incorporate Federal Reserve economic data, economic-regime classification, PostgreSQL, advanced SQL, and an interactive Power BI dashboard.

## Business Questions

1. How have different assets performed since 2012?
2. Which assets produced the strongest compound growth?
3. How much volatility accompanied those returns?
4. Which assets experienced the most severe drawdowns?
5. How do asset returns change during different inflation and interest-rate environments?
6. Which assets offer the strongest diversification benefits?

## Assets Analyzed

| Ticker | Exposure |
|---|---|
| SPY | US large-cap stocks |
| QQQ | US growth and Nasdaq-100 stocks |
| SCHD | US dividend stocks |
| IWM | US small-cap stocks |
| TLT | Long-term US Treasury bonds |
| GLD | Gold |

QQQ is used instead of QQQM because its longer history supports analysis across more market environments.

## Technology Stack

- Python
- pandas
- NumPy
- yfinance
- Matplotlib
- Seaborn
- Git and GitHub
- PostgreSQL and SQL — planned
- Power BI — planned
- FRED API — planned

## Current Data Pipeline

```text
Yahoo Finance
      ↓
Python data extraction
      ↓
Raw adjusted prices
      ↓
Data validation
      ↓
Return and risk calculations
      ↓
Processed analytical dataset
      ↓
Static financial visualizations
```

Downloaded and generated datasets are excluded from Git because they can be reproduced by running the project scripts.

## Metrics Calculated

- Daily returns
- Growth of an initial $1 investment
- Rolling 21-day annualized volatility
- Rolling 252-day return
- Compound annual growth rate
- Full-period annualized volatility
- Maximum drawdown

## Preliminary Results

Results below cover January 2012 through September 18, 2026.

| Ticker | Total Return | Annualized Volatility | Maximum Drawdown |
|---|---:|---:|---:|
| QQQ | 1,335.51% | 20.51% | -35.12% |
| SPY | 670.85% | 16.52% | -33.72% |
| SCHD | 507.07% | 15.26% | -33.37% |
| IWM | 361.90% | 21.13% | -41.13% |
| GLD | 157.29% | 16.49% | -42.11% |
| TLT | 2.45% | 14.38% | -48.35% |

## Initial Findings

- QQQ generated the strongest compound growth, although it carried more volatility than SPY and SCHD.
- SPY produced substantially stronger returns than IWM despite having lower volatility.
- SCHD delivered lower volatility and a slightly smaller maximum drawdown than SPY.
- Gold produced positive long-term growth but still experienced a drawdown exceeding 40%.
- Long-term Treasury bonds performed poorly over the sample and experienced the most severe maximum drawdown.
- The results demonstrate why return alone is insufficient when comparing investments.

## Visualizations

### Growth of $1

![Growth of $1 invested](dashboard/screenshots/growth_of_one.png)

### Risk and Return

![Annualized return versus volatility](dashboard/screenshots/risk_return_scatter.png)

### Maximum Drawdown

![Maximum drawdown by asset](dashboard/screenshots/maximum_drawdown.png)

## Repository Structure

```text
market-regime-analytics/
├── dashboard/
│   └── screenshots/
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
├── reports/
├── sql/
├── src/
│   ├── download_market_data.py
│   ├── calculate_market_metrics.py
│   └── create_market_charts.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Running the Project

Clone the repository:

```bash
git clone https://github.com/JoelTul/market-regime-analytics.git
cd market-regime-analytics
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the pipeline in order:

```bash
python src/download_market_data.py
python src/calculate_market_metrics.py
python src/create_market_charts.py
```

## Project Roadmap

- [x] Create the GitHub project structure
- [x] Download adjusted ETF price histories
- [x] Add data-quality validation
- [x] Calculate return and risk metrics
- [x] Generate static analytical visualizations
- [ ] Integrate Federal Reserve economic data
- [ ] Calculate inflation and interest-rate changes
- [ ] Classify economic regimes
- [ ] Analyze asset performance within each regime
- [ ] Load analytical data into PostgreSQL
- [ ] Develop advanced SQL queries and views
- [ ] Build an interactive Power BI dashboard
- [ ] Document final investment insights

## Limitations

- Historical performance does not predict future results.
- Results depend on the selected assets and January 2012 starting date.
- The analysis does not currently include taxes, trading costs, or a risk-free benchmark.
- Market data should be treated as research data rather than institutional-grade pricing.
- Economic-regime analysis has not yet been implemented.

## Author

Joel Tulanowski