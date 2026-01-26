"""
GSE CSV Upload Processor
Processes uploaded GSE CSV files and updates individual seed files
"""

import pandas as pd
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SEEDS_FOLDER = PROJECT_ROOT / "seeds"
UPLOADS_FOLDER = PROJECT_ROOT / "uploads"

def process_uploads():
    """Process all CSV files in the uploads folder"""
    
    if not UPLOADS_FOLDER.exists():
        print("No uploads folder found")
        return
    
    csv_files = list(UPLOADS_FOLDER.glob("*.csv"))
    if not csv_files:
        print("No CSV files to process")
        return
    
    print(f"Found {len(csv_files)} CSV file(s) to process")
    
    total_updated = 0
    
    for csv_file in csv_files:
        print(f"\nProcessing: {csv_file.name}")
        try:
            df = pd.read_csv(csv_file)
            updated = process_file(df)
            total_updated += updated
            
            # Delete processed file
            os.remove(csv_file)
            print(f"  Deleted: {csv_file.name}")
            
        except Exception as e:
            print(f"  Error processing {csv_file.name}: {e}")
    
    print(f"\nTotal records updated: {total_updated}")

def process_file(df):
    """Process a single CSV file and update seed files"""
    updated = 0
    
    # Process in reverse order so newest dates end up on top
    for _, row in df.iloc[::-1].iterrows():
        symbol = row.get('Share Code')
        
        # Skip empty symbols
        if pd.isna(symbol) or str(symbol).strip() == '':
            continue
        
        # Clean symbol (remove asterisks)
        symbol = str(symbol)
        clean_symbol = symbol.replace('*', '').strip()
        
        # Find matching seed file
        seed_file = find_seed_file(symbol, clean_symbol)
        if not seed_file:
            continue
        
        # Check for duplicates and update
        if update_seed_file(seed_file, row):
            print(f"  Updated: {seed_file.stem} - {row.get('Daily Date')}")
            updated += 1
    
    return updated

def find_seed_file(symbol, clean_symbol):
    """Find matching seed file (case-insensitive)"""
    for f in SEEDS_FOLDER.glob("*.csv"):
        if f.stem.upper() == symbol.upper() or f.stem.upper() == clean_symbol.upper():
            return f
    return None

def update_seed_file(seed_file, row):
    """Update a seed file with new data, checking for duplicates"""
    try:
        seed_df = pd.read_csv(seed_file)
        
        daily_date = row.get('Daily Date')
        if pd.isna(daily_date):
            return False
        
        # Check for duplicate
        if daily_date in seed_df['Daily Date'].values:
            return False
        
        # Prepend new row
        new_row = pd.DataFrame([row])
        seed_df = pd.concat([new_row, seed_df], ignore_index=True)
        seed_df.to_csv(seed_file, index=False)
        return True
        
    except Exception as e:
        print(f"    Error updating {seed_file.name}: {e}")
        return False

if __name__ == "__main__":
    process_uploads()
