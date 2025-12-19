import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

# CONFIG
DATA_FILE = 'gse_data.csv'
URL = "https://afx.kwayisi.org/gse/" 

def fetch_todays_prices():
    print("Fetching today's prices...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        page = requests.get(URL, headers=headers)
        soup = BeautifulSoup(page.content, 'html.parser')
        table = soup.find('table')
        
        new_data = []
        today_str = datetime.now().strftime("%d/%m/%Y") # Matches your CSV format: DD/MM/YYYY
        
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) > 3:
                symbol = cols[0].text.strip()
                try:
                    # Clean price (remove commas)
                    price = float(cols[2].text.strip().replace(',', ''))
                    
                    # Create row matching your historical CSV structure
                    new_data.append({
                        'Date': today_str,  # Matches "Daily Date" parsing logic in app.py
                        'Symbol': symbol,   # Matches "Share Code" logic
                        'Close': price      # Matches "Closing Price" logic
                    })
                except ValueError:
                    continue
        return pd.DataFrame(new_data)
    except Exception as e:
        print(f"Error scraping: {e}")
        return pd.DataFrame()

def update_csv():
    # Only try to update if the master file exists (created by app.py)
    if os.path.exists(DATA_FILE):
        try:
            existing_df = pd.read_csv(DATA_FILE)
            todays_df = fetch_todays_prices()
            
            if not todays_df.empty:
                # Convert 'Date' to datetime for comparison
                # Note: app.py standardizes everything to 'Date', 'Symbol', 'Close'
                # so we stick to that schema for the master file.
                
                # Check if today is already in the file to avoid dupes
                today_dt = pd.to_datetime(datetime.now().date())
                
                if 'Date' in existing_df.columns:
                    existing_df['Date'] = pd.to_datetime(existing_df['Date'])
                    existing_df = existing_df[existing_df['Date'] != today_dt]
                
                # Combine
                updated_df = pd.concat([existing_df, todays_df], ignore_index=True)
                updated_df['Date'] = pd.to_datetime(updated_df['Date']) # Ensure datetime
                updated_df = updated_df.sort_values(['Date', 'Symbol'])
                
                updated_df.to_csv(DATA_FILE, index=False)
                print(f"Updated data with {len(todays_df)} new rows.")
            else:
                print("No new data found today.")
        except Exception as e:
            print(f"Failed to update CSV: {e}")
    else:
        print("Master CSV not found. The Streamlit app needs to run at least once to create it from seeds.")

if __name__ == "__main__":
    update_csv()
