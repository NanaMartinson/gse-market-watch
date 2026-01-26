# GSE Market Watch

A market intelligence terminal for the Ghana Stock Exchange.

![GSE Market Watch](https://img.shields.io/badge/GSE-Market%20Watch-yellow)

## Features

- 📈 Interactive price charts with moving averages
- 📊 Yahoo Finance-style metrics (52-week high/low, volume, volatility)
- 🔍 Stock search and filtering
- 📥 CSV download for any stock
- 🌙 Dark theme
- 🔄 Automated daily updates

## Project Structure

```
gse-market-watch/
├── public/
│   ├── gse_data.json      # Generated data file
│   └── favicon.svg
├── seeds/                  # Your historical CSV files
│   ├── ACCESS.csv
│   ├── GCB.csv
│   └── ...
├── scripts/
│   └── build_data.py      # Converts CSVs to JSON
├── src/
│   ├── App.jsx            # Main React component
│   ├── main.jsx
│   └── index.css
├── .github/
│   └── workflows/
│       └── daily_update.yml
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── README.md
```

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/yourusername/gse-market-watch.git
cd gse-market-watch
npm install
```

### 2. Add your seed data

Place your stock CSV files in the `seeds/` folder. Each CSV should have columns:
- `Daily Date` (DD/MM/YYYY)
- `Share Code`
- `Closing Price - VWAP (GH¢)`
- Plus other columns (volume, year high/low, etc.)

### 3. Generate the data file

```bash
python scripts/build_data.py
```

This creates `public/gse_data.json` which the React app reads.

### 4. Run locally

```bash
npm run dev
```

Open http://localhost:5173

## Deploy to Vercel

### Option 1: One-Click Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/gse-market-watch)

### Option 2: Manual Setup

1. Push your repo to GitHub
2. Go to [vercel.com](https://vercel.com) and sign in with GitHub
3. Click "Add New Project"
4. Import your repository
5. Vercel auto-detects Vite - just click Deploy
6. Done! Your site is live.

## Automated Updates

The GitHub Action (`.github/workflows/daily_update.yml`) runs daily at 6 PM UTC:

1. Pulls latest code
2. Runs `build_data.py` to regenerate JSON from CSVs
3. Commits and pushes changes
4. Vercel auto-deploys the update

To trigger manually: Go to Actions → Daily Data Update → Run workflow

## Easy Upload Method

You can update the stock data by uploading CSV files directly on GitHub:

1. Download the daily prices CSV from the GSE website
2. Go to the [`uploads/`](./uploads) folder in this repository
3. Click "Add file" → "Upload files"
4. Drag and drop your CSV file(s)
5. Click "Commit changes"
6. The GitHub Action will automatically:
   - Update all seed files
   - Regenerate the JSON data
   - Delete the uploaded CSV
   - Deploy the changes

Check the [Actions tab](../../actions) to monitor progress.

## Adding New Stocks

1. Add the CSV file to `seeds/` folder
2. (Optional) Add the stock name and sector to `scripts/build_data.py`:
   ```python
   STOCK_NAMES = {
       "NEWSTOCK": "New Stock Company Ltd",
       ...
   }
   ```
3. Run `python scripts/build_data.py`
4. Commit and push

## Tech Stack

- **Frontend**: React + Vite + Tailwind CSS
- **Charts**: Recharts
- **Icons**: Lucide React
- **Data Processing**: Python + Pandas
- **Hosting**: Vercel
- **CI/CD**: GitHub Actions

## License

MIT
