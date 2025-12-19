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
        today = datetime.now().strftime("%Y-%m-%d")
        
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) > 3:
                symbol = cols[0].text.strip()
                try:
                    price = float(cols[2].text.strip().replace(',', ''))
                    # Append new row matching the CSV structure
                    new_data.append({
                        'Date': today,
                        'Symbol': symbol,
                        'Close': price
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
        existing_df = pd.read_csv(DATA_FILE)
        todays_df = fetch_todays_prices()
        
        if not todays_df.empty:
            # Avoid duplicates: remove today's date if it already exists
            today_str = datetime.now().strftime("%Y-%m-%d")
            existing_df = existing_df[existing_df['Date'] != today_str]
            
            # Combine
            updated_df = pd.concat([existing_df, todays_df], ignore_index=True)
            updated_df = updated_df.sort_values(['Date', 'Symbol'])
            
            updated_df.to_csv(DATA_FILE, index=False)
            print(f"Updated data for {today_str}")
        else:
            print("No new data found today.")
    else:
        print("Master CSV not found. The Streamlit app needs to run at least once to create it from seeds.")

if __name__ == "__main__":
    update_csv()
