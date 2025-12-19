"""
GSE Daily Price Updater
Scrapes current prices from afx.kwayisi.org and updates the seed CSVs
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import glob

# =============================================================================
# CONFIGURATION
# =============================================================================
SEEDS_FOLDER = "seeds"
URL = "https://afx.kwayisi.org/gse/"

# Column structure matching your seed CSVs
COLUMNS = [
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table')
        
        if not table:
            print("Could not find price table on page")
            return {}
        
        prices = {}
        today_str = datetime.now().strftime("%d/%m/%Y")
        
        for row in table.find_all('tr')[1:]:  # Skip header
            cols = row.find_all('td')
            
            if len(cols) >= 5:
                symbol = cols[0].text.strip().upper()
                
                try:
                    # Parse the available data
                    # Column layout on afx: Symbol, Name, Bid, Ask, Price, Change, %Change, Volume
                    price_text = cols[4].text.strip().replace(',', '') if len(cols) > 4 else None
                    change_text = cols[5].text.strip().replace(',', '') if len(cols) > 5 else '0'
                    volume_text = cols[7].text.strip().replace(',', '') if len(cols) > 7 else '0'
                    
                    if price_text:
                        current_price = float(price_text)
                        change = float(change_text) if change_text else 0
                        prev_close = current_price - change
                        volume = float(volume_text) if volume_text else 0
                        
                        prices[symbol] = {
                            'date': today_str,
                            'close': current_price,
                            'prev_close': prev_close,
                            'change': change,
                            'volume': volume
                        }
                        
                except (ValueError, IndexError) as e:
                    continue
        
        print(f"Successfully fetched {len(prices)} stock prices")
        return prices
        
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return {}


def update_seed_files(prices):
    """Update individual seed CSV files with new prices"""
    if not prices:
        print("No prices to update")
        return
    
    if not os.path.exists(SEEDS_FOLDER):
        print(f"Seeds folder '{SEEDS_FOLDER}' not found")
        return
    
    today = datetime.now()
    today_str = today.strftime("%d/%m/%Y")
    
    updated_count = 0
    
    for symbol, data in prices.items():
        csv_path = os.path.join(SEEDS_FOLDER, f"{symbol}.csv")
        
        if not os.path.exists(csv_path):
            print(f"  No seed file for {symbol}, skipping")
            continue
        
        try:
            df = pd.read_csv(csv_path)
            
            # Check if today's data already exists
            if 'Daily Date' in df.columns:
                df['_temp_date'] = pd.to_datetime(df['Daily Date'], format='%d/%m/%Y', errors='coerce')
                
                # Remove any existing entry for today
                df = df[df['_temp_date'].dt.date != today.date()]
                df = df.drop(columns=['_temp_date'])
            
            # Create new row with available data
            new_row = {
                'Daily Date': today_str,
                'Share Code': symbol,
                'Year High (GH¢)': '',  # Will be updated from existing data
                'Year Low (GH¢)': '',
                'Previous Closing Price - VWAP (GH¢)': data['prev_close'],
                'Opening Price (GH¢)': data['prev_close'],  # Approximate
                'Last Transaction Price (GH¢)': data['close'],
                'Closing Price - VWAP (GH¢)': data['close'],
                'Price Change (GH¢)': data['change'],
                'Closing Bid Price (GH¢)': '',
                'Closing Offer Price (GH¢)': '',
                'Total Shares Traded': data['volume'],
                'Total Value Traded (GH¢)': data['volume'] * data['close']
            }
            
            # Get year high/low from existing data
            if 'Closing Price - VWAP (GH¢)' in df.columns:
                df['_close_numeric'] = pd.to_numeric(
                    df['Closing Price - VWAP (GH¢)'].astype(str).str.replace(',', ''), 
                    errors='coerce'
                )
                year_start = datetime(today.year, 1, 1)
                df['_temp_date'] = pd.to_datetime(df['Daily Date'], format='%d/%m/%Y', errors='coerce')
                year_df = df[df['_temp_date'] >= year_start]
                
                if not year_df.empty:
                    year_high = max(year_df['_close_numeric'].max(), data['close'])
                    year_low = min(year_df['_close_numeric'].min(), data['close'])
                    new_row['Year High (GH¢)'] = year_high
                    new_row['Year Low (GH¢)'] = year_low
                
                df = df.drop(columns=['_close_numeric', '_temp_date'], errors='ignore')
            
            # Append new row at the top (most recent first)
            new_df = pd.DataFrame([new_row])
            df = pd.concat([new_df, df], ignore_index=True)
            
            # Save
            df.to_csv(csv_path, index=False)
            print(f"  Updated {symbol}: GH₵{data['close']:.2f} ({data['change']:+.2f})")
            updated_count += 1
            
        except Exception as e:
            print(f"  Error updating {symbol}: {e}")
            continue
    
    print(f"\nUpdated {updated_count} files")


def main():
    """Main execution"""
    print("=" * 50)
    print("GSE Daily Price Update")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Fetch current prices
    prices = fetch_current_prices()
    
    if prices:
        # Update seed files
        update_seed_files(prices)
        print("\nUpdate complete!")
    else:
        print("\nNo data fetched. Update skipped.")


if __name__ == "__main__":
    main()
