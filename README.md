# Stock Market ETL Pipeline

ETL project that downloads historical
stock prices from Yahoo Finance, turns them into an analytics-ready dataset, runs
data quality checks, and incrementally loads new records into SQLite.

## Architecture

```text
Yahoo Finance (yfinance)
          |
          v
    Extract raw prices
          |
          v
 Transform and calculate returns
          |
          v
     Data quality checks
          |
          v
 SQLite: fact_stock_prices
          |
          v
 Future BI and cloud services
```

The code is separated into extraction, transformation, validation, and loading
modules so each part can later be replaced independently.

## Tech Stack

- Python 3.11+
- yfinance
- pandas
- SQLAlchemy
- SQLite
- python-dotenv
- pytest

## Project Structure

```text
stock-market-etl-pipeline/
|-- data/
|   `-- stock_market.db        # Created on the first pipeline run
|-- src/
|   |-- __init__.py
|   |-- config.py
|   |-- extract.py
|   |-- transform.py
|   |-- load.py
|   |-- quality_checks.py
|   `-- main.py
|-- tests/
|   |-- test_transform.py
|   `-- test_quality_checks.py
|-- .env.example
|-- .gitignore
|-- requirements.txt
`-- README.md
```

## Setup

Run these commands from PowerShell in VS Code:

```powershell
cd stock-market-etl-pipeline
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

The default `.env` configuration downloads six months of daily prices for AAPL,
MSFT, NVDA, GOOGL, and AMZN. Edit it to use different tickers, periods, or a
different SQLAlchemy database URL.

## Run the Pipeline

From the project root folder `stock-market-etl-pipeline`, run:

```powershell
cd stock-market-etl-pipeline
python -m src.main
```

If you are already inside `stock-market-etl-pipeline`, just run:

```powershell
python -m src.main
```

Example output:

```text
ETL pipeline completed successfully.
Tickers processed: AAPL, MSFT, NVDA, GOOGL, AMZN
Rows extracted: 630
Rows loaded: 630
Database: data\stock_market.db
Pipeline status: SUCCESS
```

On later runs, `Rows loaded` may be zero or a small number. The loader checks
existing `ticker` and `price_date` combinations and appends only new records.

## Database Table

The pipeline creates `fact_stock_prices` with these columns:

| Column | Description |
|---|---|
| `ticker` | Stock ticker symbol |
| `price_date` | Trading date |
| `open_price` | Opening price |
| `high_price` | Daily high |
| `low_price` | Daily low |
| `close_price` | Closing price |
| `adj_close_price` | Split- and dividend-adjusted close |
| `volume` | Number of shares traded |
| `daily_return` | Percentage change in close price from the prior trading day |
| `loaded_at` | UTC timestamp when the ETL batch was transformed |

A unique database constraint on `ticker` and `price_date` provides additional
duplicate protection.

## Tests

```powershell
pytest
```

The tests cover daily return calculations, transformation deduplication,
duplicate quality checks, and negative-price validation.

## Future Improvements

- Replace SQLite with Azure SQL for a managed cloud warehouse
- Land raw extracts in Azure Blob Storage
- Schedule and monitor the workflow with Apache Airflow
- Build a Power BI dashboard for price and return analysis
- Add a Kafka and Spark streaming version for near-real-time market events


