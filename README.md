# GSE Market Watch

A market intelligence terminal for the Ghana Stock Exchange built with Streamlit.

## Features

- **Interactive Price Charts** - Candlestick-style area charts with volume overlay
- **Yahoo Finance-style Metrics**:
  - Current price with daily change
  - 52-week high/low
  - Moving averages (20, 50, 200-day)
  - Volume analytics (current, 10-day avg, 30-day avg)
  - Bid/Ask spread
  - Volatility (30-day annualized)
  - Performance returns (1W, 1M, 3M, 6M, 1Y, YTD)
- **Stock Search** - Filter stocks by symbol
- **Data Download** - Export any stock's history as CSV
- **Dark Theme** - Easy on the eyes
- **Daily Updates** - Scraper to keep data current

## Project Structure

```
gse_terminal/
├── app.py              # Main Streamlit application
├── daily_update.py     # Price scraper for daily updates
├── requirements.txt    # Python dependencies
├── seeds/              # Your historical CSV files go here
│   ├── ACCESS.csv
│   ├── GCB.csv
│   └── ... (one file per stock)
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Add Your Data

Place your stock CSV files in the `seeds/` folder. Each file should have these columns:
- `Daily Date` (DD/MM/YYYY format)
- `Share Code`
- `Closing Price - VWAP (GH¢)`
- Plus any additional columns (volume, bid/ask, etc.)

### 3. Run Locally

```bash
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set the main file path to `app.py`
5. Deploy!

## Daily Updates

To fetch and update prices automatically:

### Manual Run
```bash
python daily_update.py
```

### GitHub Actions (Automated)

Create `.github/workflows/daily_update.yml`:

```yaml
name: Daily GSE Update

on:
  schedule:
    - cron: '0 17 * * 1-5'  # 5 PM UTC, Mon-Fri
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests beautifulsoup4 pandas
      
      - name: Run update script
        run: python daily_update.py
      
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add seeds/
          git diff --quiet && git diff --staged --quiet || git commit -m "Daily price update $(date +'%Y-%m-%d')"
          git push
```

## Data Source

Historical data: Your seed CSVs (GSE official data)
Daily updates: [AFX Ghana](https://afx.kwayisi.org/gse/)

## License

MIT
