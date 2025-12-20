"""
GSE Daily Price Scraper
Fetches current prices from dev.kwayisi.org API and updates the seed CSVs
"""

import pandas as pd
import requests
import time
from datetime import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SEEDS_FOLDER = PROJECT_ROOT / "seeds"

# API endpoints to try (in order of preference)
API_ENDPOINTS = [
    "https://dev.kwayisi.org/apis/gse/live",
    "https://dev.kwayisi.org/apis/gse/equities",
]

# Expected columns in seed CSVs
SEED_COLUMNS = [
    "Daily Date",
    "Share Code",
    "Year High (GH¢)",
    "Year Low (GH¢)",
    "Previous Closing Price - VWAP (GH¢)",
    "Opening Price (GH¢)",
    "Last Transaction Price (GH¢)",
    "Closing Price - VWAP (GH¢)",
    "Price Change (GH¢)",
    "Closing Bid Price (GH¢)",
    "Closing Offer Price (GH¢)",
    "Total Shares Traded",
    "Total Value Traded (GH¢)"
]


def fetch_current_prices():
    """Fetch current prices from kwayisi GSE API with retries"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    for url in API_ENDPOINTS:
        print(f"Trying {url}...")
        
        # Retry up to 3 times per endpoint
        for attempt in range(3):
            try:
                print(f"  Attempt {attempt + 1}/3...")
                response = requests.get(url, headers=headers, timeout=90)
                response.raise_for_status()
                
                data = response.json()
                
                if not isinstance(data, list):
                    print(f"  Unexpected response format from {url}")
                    break  # Try next endpoint
                
                prices = {}
                
                for stock in data:
                    try:
                        # API returns: {"name": "SYMBOL", "price": X.XX, "change": X.XX, "volume": XXX}
                        symbol = stock.get('name', '').strip().upper()
                        
                        if not symbol:
                            continue
                        
                        current_price = float(stock.get('price', 0))
                        change = float(stock.get('change', 0))
                        volume = int(stock.get('volume', 0))
                        
                        if current_price <= 0:
                            continue
                        
                        # Calculate previous close
                        prev_close = current_price - change
                        
                        prices[symbol] = {
                            'price': current_price,
                            'change': change,
                            'prev_close': prev_close,
                            'volume': volume
                        }
                        
                    except (ValueError, TypeError, KeyError):
                        continue
                
                if prices:
                    print(f"  Successfully fetched {len(prices)} stock prices")
                    return prices
                else:
                    print(f"  No valid prices in response")
                    break  # Try next endpoint
                    
            except requests.exceptions.Timeout:
                print(f"  Timeout on attempt {attempt + 1}")
                if attempt < 2:
                    print(f"  Waiting 10 seconds before retry...")
                    time.sleep(10)
            except requests.exceptions.RequestException as e:
                print(f"  Error: {e}")
                if attempt < 2:
                    print(f"  Waiting 5 seconds before retry...")
                    time.sleep(5)
    
    print("All endpoints failed")
    return {}


def update_seed_file(symbol, data, today_str):
    """Update a single seed CSV file with new price data"""
    
    # Find matching seed file (case-insensitive)
    seed_file = None
    for f in SEEDS_FOLDER.glob("*.csv"):
        if f.stem.upper() == symbol.upper():
            seed_file = f
            break
    
    if not seed_file:
        # Also check for exact match
        potential_file = SEEDS_FOLDER / f"{symbol}.csv"
        if potential_file.exists():
            seed_file = potential_file
    
    if not seed_file:
        return False
    
    try:
        df = pd.read_csv(seed_file)
        
        # Check if today's data already exists
        if 'Daily Date' in df.columns:
            # Parse existing dates
            df['_temp_date'] = pd.to_datetime(df['Daily Date'], format='%d/%m/%Y', errors='coerce')
            today_dt = datetime.strptime(today_str, '%d/%m/%Y').date()
            
            # Remove any existing entry for today
            mask = df['_temp_date'].dt.date != today_dt
            df = df[mask].drop(columns=['_temp_date'])
        
        # Get year high/low from existing data
        year_high = data['price']
        year_low = data['price']
        
        if 'Year High (GH¢)' in df.columns and len(df) > 0:
            try:
                existing_high = pd.to_numeric(df['Year High (GH¢)'].iloc[0], errors='coerce')
                if pd.notna(existing_high) and existing_high > 0:
                    year_high = max(existing_high, data['price'])
            except:
                pass
                
        if 'Year Low (GH¢)' in df.columns and len(df) > 0:
            try:
                existing_low = pd.to_numeric(df['Year Low (GH¢)'].iloc[0], errors='coerce')
                if pd.notna(existing_low) and existing_low > 0:
                    year_low = min(existing_low, data['price'])
            except:
                pass
        
        # Create new row
        new_row = {
            'Daily Date': today_str,
            'Share Code': symbol,
            'Year High (GH¢)': year_high,
            'Year Low (GH¢)': year_low,
            'Previous Closing Price - VWAP (GH¢)': data['prev_close'],
            'Opening Price (GH¢)': data['prev_close'],
            'Last Transaction Price (GH¢)': data['price'],
            'Closing Price - VWAP (GH¢)': data['price'],
            'Price Change (GH¢)': data['change'],
            'Closing Bid Price (GH¢)': '',
            'Closing Offer Price (GH¢)': '',
            'Total Shares Traded': data['volume'],
            'Total Value Traded (GH¢)': data['volume'] * data['price']
        }
        
        # Add new row at the top
        new_df = pd.DataFrame([new_row])
        df = pd.concat([new_df, df], ignore_index=True)
        
        # Save
        df.to_csv(seed_file, index=False)
        return True
        
    except Exception as e:
        print(f"  Error updating {symbol}: {e}")
        return False


def main():
    print("=" * 50)
    print("GSE Daily Price Scraper")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Check seeds folder
    if not SEEDS_FOLDER.exists():
        print(f"Error: Seeds folder not found at {SEEDS_FOLDER}")
        return
    
    # Get list of existing seed files
    seed_files = list(SEEDS_FOLDER.glob("*.csv"))
    seed_symbols = {f.stem.upper() for f in seed_files}
    print(f"Found {len(seed_files)} seed files")
    
    # Fetch current prices
    prices = fetch_current_prices()
    
    if not prices:
        print("No prices fetched. Exiting.")
        return
    
    # Today's date in format matching CSVs
    today_str = datetime.now().strftime('%d/%m/%Y')
    
    # Update seed files
    print(f"\nUpdating seed files for {today_str}...")
    updated = 0
    skipped = 0
    not_found = []
    
    for symbol, data in prices.items():
        # Check if we have a seed file for this symbol
        if symbol.upper() in seed_symbols:
            if update_seed_file(symbol, data, today_str):
                print(f"  ✓ {symbol}: GH₵{data['price']:.2f} ({data['change']:+.2f})")
                updated += 1
            else:
                skipped += 1
        else:
            # Try common variations
            variations = [symbol, symbol.replace(' ', ''), f"{symbol}.GH"]
            found = False
            for var in variations:
                if var.upper() in seed_symbols:
                    if update_seed_file(var, data, today_str):
                        print(f"  ✓ {var}: GH₵{data['price']:.2f} ({data['change']:+.2f})")
                        updated += 1
                        found = True
                        break
            if not found:
                not_found.append(symbol)
    
    print(f"\nSummary:")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print(f"  No seed file: {len(not_found)}")
    if not_found:
        print(f"  Missing: {', '.join(not_found[:10])}{'...' if len(not_found) > 10 else ''}")
    print("Done!")


if __name__ == "__main__":
    main()
