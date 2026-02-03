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

### Daily Data Refresh

The GitHub Action (`.github/workflows/daily_update.yml`) runs daily at 6 PM UTC:

1. Pulls latest code
2. Runs `build_data.py` to regenerate JSON from CSVs
3. Commits and pushes changes
4. Vercel auto-deploys the update

To trigger manually: Go to Actions → Daily Data Update → Run workflow

### CSV Upload Processing

You can now upload GSE CSV files directly to GitHub instead of running scripts locally!

**How to upload new data:**

1. Download the CSV file(s) from the GSE website
2. Go to your repository on GitHub.com
3. Navigate to the `uploads/` folder
4. Click **"Add file"** → **"Upload files"**
5. Drag and drop your GSE CSV file(s)
6. Click **"Commit changes"** (commit directly to main branch)
7. Wait for the GitHub Action to process (check the **Actions** tab for status)

**What happens automatically:**

- The workflow reads all CSV files from `uploads/`
- Updates the matching seed files in `seeds/` folder (skips duplicate dates)
- Regenerates `public/gse_data.json`
- Deletes the processed CSV files from `uploads/`
- Commits and pushes all changes
- Vercel auto-deploys the updated site

**Supported formats:**
- Single day files: `GSE Share Prices 5th January 2026.csv`
- Multi-day files: `GSE Share Prices 7th to 16th January 2026.csv`

**💡 Cost-Free Operation:**
- This workflow uses **NO external API calls** or premium services
- It only processes local CSV files and commits to your repository
- Uses GitHub Actions free tier (2,000 minutes/month for public repos)
- Typical run takes ~30-60 seconds
- **Note:** The `scrape_prices.py` script (which does make external API calls) is NOT used by any workflow

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
