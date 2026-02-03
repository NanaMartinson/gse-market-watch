"""
Process uploaded GSE CSV files and update seed files.
This script is designed to be run by GitHub Actions when CSV files
are uploaded to the uploads/ folder.

IMPORTANT: This script makes NO external API calls and uses NO premium services.
It only reads/writes local CSV files in the repository.
"""

import pandas as pd
from pathlib import Path
import sys

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
UPLOADS_FOLDER = PROJECT_ROOT / "uploads"
SEEDS_FOLDER = PROJECT_ROOT / "seeds"


def clean_symbol(symbol):
    """Remove asterisks and clean symbol name"""
    if pd.isna(symbol):
        return None
    return str(symbol).replace('*', '').strip()


def find_seed_file(symbol, clean_sym):
    """Find matching seed file (case-insensitive)"""
    if not clean_sym:
        return None
    for seed_file in SEEDS_FOLDER.glob("*.csv"):
        stem = seed_file.stem.upper()
        # Try both original and cleaned symbol
        if stem == str(symbol).upper() or stem == clean_sym.upper():
            return seed_file
    return None


def process_csv_file(csv_path):
    """Process a single uploaded CSV file"""
    print(f"\n📄 Processing: {csv_path.name}")
    
    try:
        # Read the uploaded CSV
        df = pd.read_csv(csv_path)
        
        if df.empty:
            print(f"  ⚠️  File is empty, skipping")
            return 0
        
        # Sort by date (oldest first) so we process chronologically
        # Parse dates to sort properly
        df['_parsed_date'] = pd.to_datetime(df['Daily Date'], format='%d/%m/%Y', errors='coerce')
        
        # Check for unparseable dates
        invalid_dates = df[df['_parsed_date'].isna()]
        if not invalid_dates.empty:
            print(f"  ⚠️  Warning: Found {len(invalid_dates)} row(s) with invalid dates, skipping them")
            for idx in invalid_dates.index:
                date_val = df.loc[idx, 'Daily Date']
                print(f"      Row {idx}: Invalid date '{date_val}'")
        
        # Filter out rows with invalid dates
        df = df[df['_parsed_date'].notna()]
        
        df = df.sort_values('_parsed_date')
        df = df.drop(columns=['_parsed_date'])
        
        updates_count = 0
        
        # Process each row
        for _, row in df.iterrows():
            symbol = row['Share Code']
            
            # Skip rows with empty Share Code
            if pd.isna(symbol) or str(symbol).strip() == '':
                continue
            
            # Clean the symbol
            clean_sym = clean_symbol(symbol)
            if not clean_sym:
                continue
            
            # Find matching seed file
            seed_file = find_seed_file(symbol, clean_sym)
            if not seed_file:
                print(f"  ⚠️  No seed file found for symbol: {symbol} (cleaned: {clean_sym})")
                continue
            
            # Read existing seed file
            seed_df = pd.read_csv(seed_file)
            
            # Check if this date already exists
            daily_date = row['Daily Date']
            if daily_date in seed_df['Daily Date'].values:
                # Skip duplicate
                continue
            
            # Prepend the new row to the seed file
            # Create a single-row DataFrame from the row
            new_row_df = pd.DataFrame([row])
            seed_df = pd.concat([new_row_df, seed_df], ignore_index=True)
            
            # Write back to seed file
            seed_df.to_csv(seed_file, index=False)
            
            print(f"  ✅ Updated {seed_file.name}: Added {daily_date} for {symbol}")
            updates_count += 1
        
        return updates_count
        
    except Exception as e:
        print(f"  ❌ Error processing {csv_path.name}: {e}")
        return 0


def main():
    print("=" * 60)
    print("GSE CSV Upload Processor")
    print("=" * 60)
    
    # Check if uploads folder exists
    if not UPLOADS_FOLDER.exists():
        print(f"❌ Uploads folder not found: {UPLOADS_FOLDER}")
        sys.exit(1)
    
    # Check if seeds folder exists
    if not SEEDS_FOLDER.exists():
        print(f"❌ Seeds folder not found: {SEEDS_FOLDER}")
        sys.exit(1)
    
    # Find all CSV files in uploads folder
    csv_files = sorted(UPLOADS_FOLDER.glob("*.csv"))
    
    if not csv_files:
        print("ℹ️  No CSV files found in uploads folder")
        return
    
    print(f"Found {len(csv_files)} CSV file(s) to process\n")
    
    total_updates = 0
    processed_files = []
    
    # Process each CSV file
    for csv_file in csv_files:
        updates = process_csv_file(csv_file)
        total_updates += updates
        processed_files.append(csv_file)
    
    print("\n" + "=" * 60)
    print(f"✅ Processing complete!")
    print(f"   Total updates: {total_updates}")
    print(f"   Files processed: {len(processed_files)}")
    
    # Delete processed files
    if processed_files:
        print("\n🗑️  Cleaning up processed files...")
        for csv_file in processed_files:
            try:
                csv_file.unlink()
                print(f"   Deleted: {csv_file.name}")
            except Exception as e:
                print(f"   ⚠️  Could not delete {csv_file.name}: {e}")
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()
