"""
GSE Daily Price Scraper
Scrapes current prices from afx.kwayisi.org and updates the seed CSVs
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import re

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SEEDS_FOLDER = PROJECT_ROOT / "seeds"

# Source URL
URL = "https://afx.kwayisi.org/gse/"

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
    """Scrape current prices from AFX Ghana"""
    print(f"Fetching prices from {URL}...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table')
        
        if not table:
            print("Could not find price table on page")
            return {}
        
        prices = {}
        
        # Parse table rows
        rows = table.find_all('tr')
        print(f"Found {len(rows)} rows in table")
        
        for row in rows[1:]:  # Skip header
            cols = row.find_all('td')
            
            if len(cols) >= 5:
                try:
                    # Extract symbol (first column, get the link text)
                    symbol_elem = cols[0].find('a')
                    if symbol_elem:
                        symbol = symbol_elem.text.strip().upper()
                    else:
                        symbol = cols[0].text.strip().upper()
                    
                    # Skip if no valid symbol
                    if not symbol or len(symbol) > 20:
                        continue
                    
                    # Get company name (second column)
                    name = cols[1].text.strip() if len(cols) > 1 else symbol
                    
                    # Parse price (usually column 4 or 5 depending on layout)
                    price_text = None
                    for i in [4, 3, 2]:
                        if len(cols) > i:
                            text = cols[i].text.strip().replace(',', '')
                            # Check if it looks like a price
                            if re.match(r'^[\d.]+$', text):
                                price_text = text
                                break
                    
                    if not price_text:
                        continue
                    
                    current_price = float(price_text)
                    
                    # Try to get change
                    change = 0.0
                    if len(cols) > 5:
                        change_text = cols[5].text.strip().replace(',', '').replace('+', '')
                        try:
                            change = float(change_text)
                        except ValueError:
                            change = 0.0
                    
                    # Calculate previous close
                    prev_close = current_price - change
                    
                    # Try to get volume
                    volume = 0
                    if len(cols) > 7:
                        vol_text = cols[7].text.strip().replace(',', '')
                        try:
                            volume = int(float(vol_text))
                        except ValueError:
                            volume = 0
                    
                    prices[symbol] = {
                        'name': name,
                        'price': current_price,
                        'change': change,
                        'prev_close': prev_close,
                        'volume': volume
                    }
                    
                except (ValueError, IndexError) as e:
                    continue
        
        print(f"Successfully parsed {len(prices)} stock prices")
        return prices
        
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
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
        print(f"  No seed file found for {symbol}")
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
                print(f"  - {symbol}: No matching seed file")
                skipped += 1
    
    print(f"\nSummary: {updated} updated, {skipped} skipped")
    print("Done!")


if __name__ == "__main__":
    main()
