"""
Converts seed CSVs to gse_data.json for the React frontend
Run this locally or via GitHub Actions before deploy
"""

import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

# Paths - works both locally and in GitHub Actions
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SEEDS_FOLDER = PROJECT_ROOT / "seeds"
OUTPUT_FILE = PROJECT_ROOT / "public" / "gse_data.json"

# Column mapping
COL_MAP = {
    "Daily Date": "date",
    "Share Code": "symbol",
    "Year High (GH¢)": "year_high",
    "Year Low (GH¢)": "year_low",
    "Previous Closing Price - VWAP (GH¢)": "prev_close",
    "Opening Price (GH¢)": "open",
    "Closing Price - VWAP (GH¢)": "close",
    "Price Change (GH¢)": "change",
    "Total Shares Traded": "volume",
    "Total Value Traded (GH¢)": "turnover"
}

# Stock name mapping
STOCK_NAMES = {
    "ACCESS": "Access Bank Ghana",
    "AADS": "AngloGold Ashanti (Dep)",
    "ADB": "Agricultural Development Bank",
    "AGA": "AngloGold Ashanti",
    "ALLGH": "Alliance Insurance",
    "ALW": "Aluworks Limited",
    "ASG": "Aradel Holdings",
    "BOPP": "Benso Oil Palm Plantation",
    "CAL": "CalBank Limited",
    "CLYD": "Clydestone Ghana",
    "CMLT": "Camelot Ghana",
    "CPC": "Cocoa Processing Company",
    "DASPHARMA": "DAS Pharma",
    "DIGICUT": "Digicut",
    "EGH": "Ecobank Ghana",
    "EGL": "Enterprise Group Limited",
    "ETI": "Ecobank Transnational Inc",
    "FML": "Fan Milk Limited",
    "GCB": "GCB Bank Limited",
    "GGBL": "Guinness Ghana Breweries",
    "GLD": "NewGold ETF",
    "GOIL": "Ghana Oil Company",
    "HORDS": "Hords Limited",
    "IIL": "Industrial & Infra",
    "MAC": "Mega African Capital",
    "MMH": "Meridian-Marshalls",
    "MTNGH": "MTN Ghana",
    "PBC": "Produce Buying Company",
    "RBGH": "Republic Bank Ghana",
    "SAMBA": "Samba Foods",
    "SCB": "Standard Chartered Bank Ghana",
    "SIC": "SIC Insurance Company",
    "SOGEGH": "Societe Generale Ghana",
    "SWL": "Sam Woode Limited",
    "TBL": "Trust Bank Gambia",
    "TLW": "Tullow Oil",
    "TOTAL": "TotalEnergies Marketing Ghana",
    "UNIL": "Unilever Ghana"
}

STOCK_SECTORS = {
    "ACCESS": "Banking",
    "ADB": "Banking",
    "CAL": "Banking",
    "EGH": "Banking",
    "ETI": "Banking",
    "GCB": "Banking",
    "RBGH": "Banking",
    "SCB": "Banking",
    "SOGEGH": "Banking",
    "TBL": "Banking",
    "SIC": "Insurance",
    "EGL": "Insurance",
    "ALLGH": "Insurance",
    "MTNGH": "Telecommunications",
    "GOIL": "Oil & Gas",
    "TOTAL": "Oil & Gas",
    "TLW": "Oil & Gas",
    "GGBL": "Manufacturing",
    "FML": "Manufacturing",
    "UNIL": "Manufacturing",
    "ALW": "Manufacturing",
    "CPC": "Manufacturing",
    "CMLT": "Manufacturing",
    "BOPP": "Agriculture",
    "PBC": "Agriculture",
    "SAMBA": "Food & Beverage",
    "AGA": "Mining",
    "AADS": "Mining",
    "GLD": "ETF",
    "ASG": "Energy",
    "DASPHARMA": "Healthcare",
    "DIGICUT": "Technology",
    "HORDS": "Real Estate",
    "IIL": "Industrial",
    "MAC": "Financial Services",
    "MMH": "Financial Services",
    "SWL": "Retail",
    "CLYD": "Manufacturing"
}


def load_all_csvs():
    """Load and combine all seed CSVs"""
    all_dfs = []
    
    if not SEEDS_FOLDER.exists():
        print(f"Error: Seeds folder not found at {SEEDS_FOLDER}")
        return pd.DataFrame()
    
    csv_files = list(SEEDS_FOLDER.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files")
    
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            df = df.rename(columns=COL_MAP)
            all_dfs.append(df)
            print(f"  Loaded {file.name}: {len(df)} rows")
        except Exception as e:
            print(f"  Error loading {file.name}: {e}")
    
    if not all_dfs:
        return pd.DataFrame()
    
    return pd.concat(all_dfs, ignore_index=True)


def clean_data(df):
    """Clean and validate data"""
    if df.empty:
        return df
    
    # Parse dates
    df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
    df = df.dropna(subset=['date'])
    
    # Clean numeric columns
    numeric_cols = ['year_high', 'year_low', 'prev_close', 'open', 'close', 
                    'change', 'volume', 'turnover']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '')
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Filter bad rows
    df = df[(df['close'] > 0.001) & (df['close'] < 10000)]
    
    # Sort and dedupe
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    df = df.drop_duplicates(subset=['symbol', 'date'], keep='last')
    
    # Calculate change percent
    df['change_pct'] = df.apply(
        lambda row: (row['change'] / row['prev_close'] * 100) 
        if pd.notna(row['prev_close']) and row['prev_close'] > 0 and pd.notna(row['change'])
        else 0, 
        axis=1
    )
    
    return df


def build_stock_data(df, symbol):
    """Build JSON structure for a single stock"""
    stock_df = df[df['symbol'] == symbol].copy()
    stock_df = stock_df.sort_values('date')
    
    if stock_df.empty:
        return None
    
    latest = stock_df.iloc[-1]
    
    # Calculate metrics
    current_price = float(latest['close'])
    prev_close = float(latest['prev_close']) if pd.notna(latest['prev_close']) else current_price
    change = float(latest['change']) if pd.notna(latest['change']) else 0
    change_pct = float(latest['change_pct']) if pd.notna(latest['change_pct']) else 0
    
    # Year high/low
    year_high = float(latest['year_high']) if pd.notna(latest['year_high']) and latest['year_high'] > 0 else stock_df['close'].max()
    year_low = float(latest['year_low']) if pd.notna(latest['year_low']) and latest['year_low'] > 0 else stock_df['close'].min()
    
    # Volume
    volume = int(latest['volume']) if pd.notna(latest['volume']) else 0
    avg_vol_10d = int(stock_df.tail(10)['volume'].mean()) if len(stock_df) >= 10 else 0
    avg_vol_30d = int(stock_df.tail(30)['volume'].mean()) if len(stock_df) >= 30 else 0
    
    # History (last 252 trading days = ~1 year)
    history = stock_df.tail(504)[['date', 'close', 'volume', 'change', 'change_pct']].copy()
    history['date'] = history['date'].dt.strftime('%Y-%m-%d')
    
    # Build history list with changePercent
    history_list = []
    for _, row in history.iterrows():
        history_list.append({
            'date': row['date'],
            'close': round(float(row['close']), 2),
            'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
            'change': round(float(row['change']), 2) if pd.notna(row['change']) else 0,
            'changePercent': round(float(row['change_pct']), 2) if pd.notna(row['change_pct']) else 0
        })
    
    return {
        "symbol": symbol,
        "name": STOCK_NAMES.get(symbol, symbol),
        "sector": STOCK_SECTORS.get(symbol, "General"),
        "price": round(current_price, 2),
        "prevClose": round(prev_close, 2),
        "change": round(change, 2),
        "changePercent": round(change_pct, 2),
        "yearHigh": round(year_high, 2),
        "yearLow": round(year_low, 2),
        "volume": volume,
        "avgVolume10d": avg_vol_10d,
        "avgVolume30d": avg_vol_30d,
        "history": history_list
    }


def main():
    print("=" * 50)
    print("Building gse_data.json")
    print("=" * 50)
    
    # Load data
    df = load_all_csvs()
    if df.empty:
        print("No data loaded. Exiting.")
        return
    
    # Clean data
    df = clean_data(df)
    print(f"\nCleaned data: {len(df)} rows, {df['symbol'].nunique()} stocks")
    
    # Build stock data
    stocks = []
    for symbol in sorted(df['symbol'].unique()):
        stock_data = build_stock_data(df, symbol)
        if stock_data:
            stocks.append(stock_data)
            print(f"  {symbol}: GH₵{stock_data['price']:.2f} ({stock_data['changePercent']:+.2f}%)")
    
    # Get latest date
    last_updated = df['date'].max().strftime('%d %b %Y')
    
    # Build output
    output = {
        "last_updated": last_updated,
        "generated_at": datetime.now().isoformat(),
        "stock_count": len(stocks),
        "stocks": stocks
    }
    
    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Write JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nWrote {OUTPUT_FILE}")
    print(f"Total stocks: {len(stocks)}")
    print("Done!")


if __name__ == "__main__":
    main()
