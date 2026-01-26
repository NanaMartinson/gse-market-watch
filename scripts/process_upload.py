"""
Process uploaded GSE CSV files and update seed files
This script is run by GitHub Actions when CSV files are uploaded to uploads/ folder
"""

import csv
import os
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
UPLOADS_FOLDER = PROJECT_ROOT / "uploads"
SEEDS_FOLDER = PROJECT_ROOT / "seeds"


def clean_symbol(symbol):
    """Remove asterisks from symbol names (e.g., **ALW** -> ALW, PBC** -> PBC)"""
    if not symbol:
        return symbol
    return symbol.replace('*', '').strip()


def find_seed_file(symbol, seeds_folder):
    """
    Find seed file for a symbol (case-insensitive match)
    Returns Path object or None
    """
    if not symbol:
        return None
    
    # Try exact match first
    exact_match = seeds_folder / f"{symbol}.csv"
    if exact_match.exists():
        return exact_match
    
    # Try case-insensitive match
    for file in seeds_folder.glob("*.csv"):
        if file.stem.upper() == symbol.upper():
            return file
        # Also check for "Symbol Asterisk.csv" format
        if file.stem.upper() == f"{symbol.upper()} ASTERISK":
            return file
    
    return None


def read_existing_dates(seed_file):
    """Read all existing dates from a seed file"""
    dates = set()
    try:
        with open(seed_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row.get('Daily Date', '').strip()
                if date:
                    dates.add(date)
    except Exception as e:
        print(f"  Warning: Could not read existing dates from {seed_file.name}: {e}")
    return dates


def prepend_row_to_seed(seed_file, row):
    """Prepend a new row to the top of a seed file"""
    try:
        # Read existing content
        with open(seed_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            # Empty file, write header and row
            with open(seed_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                writer.writeheader()
                writer.writerow(row)
            return True
        
        # Write new content with row prepended
        with open(seed_file, 'w', encoding='utf-8', newline='') as f:
            # Write header
            f.write(lines[0])
            # Write new row
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writerow(row)
            # Write existing rows
            for line in lines[1:]:
                f.write(line)
        
        return True
    except Exception as e:
        print(f"  Error prepending row to {seed_file.name}: {e}")
        return False


def process_csv_file(csv_file, seeds_folder):
    """Process a single uploaded CSV file"""
    print(f"\nProcessing: {csv_file.name}")
    print("-" * 60)
    
    rows_processed = 0
    rows_skipped = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Process rows in reverse order so newest dates end up on top
        for row in reversed(rows):
            symbol_raw = row.get('Share Code', '').strip()
            date = row.get('Daily Date', '').strip()
            
            # Skip rows with empty Share Code
            if not symbol_raw:
                rows_skipped += 1
                continue
            
            # Clean symbol name
            symbol = clean_symbol(symbol_raw)
            
            # Find matching seed file
            seed_file = find_seed_file(symbol, seeds_folder)
            if not seed_file:
                print(f"  ⚠ No seed file found for symbol: {symbol} (raw: {symbol_raw})")
                rows_skipped += 1
                continue
            
            # Check for duplicate date
            existing_dates = read_existing_dates(seed_file)
            if date in existing_dates:
                print(f"  ⏭ Skipped {symbol} {date} (already exists)")
                rows_skipped += 1
                continue
            
            # Prepend row to seed file
            if prepend_row_to_seed(seed_file, row):
                print(f"  ✓ Added {symbol} {date} to {seed_file.name}")
                rows_processed += 1
            else:
                rows_skipped += 1
        
        print("-" * 60)
        print(f"Total: {rows_processed} rows added, {rows_skipped} rows skipped\n")
        return True
        
    except Exception as e:
        print(f"Error processing {csv_file.name}: {e}")
        return False


def main():
    print("=" * 60)
    print("GSE CSV Upload Processor")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check folders exist
    if not UPLOADS_FOLDER.exists():
        print(f"\n✗ Uploads folder not found: {UPLOADS_FOLDER}")
        return
    
    if not SEEDS_FOLDER.exists():
        print(f"\n✗ Seeds folder not found: {SEEDS_FOLDER}")
        return
    
    # Find CSV files
    csv_files = list(UPLOADS_FOLDER.glob("*.csv"))
    if not csv_files:
        print("\n✓ No CSV files to process")
        return
    
    print(f"\nFound {len(csv_files)} CSV file(s) to process")
    
    # Process each CSV file
    processed_files = []
    for csv_file in csv_files:
        if process_csv_file(csv_file, SEEDS_FOLDER):
            processed_files.append(csv_file)
    
    # Delete processed CSV files
    if processed_files:
        print("\nDeleting processed CSV files:")
        for csv_file in processed_files:
            try:
                csv_file.unlink()
                print(f"  ✓ Deleted {csv_file.name}")
            except Exception as e:
                print(f"  ✗ Could not delete {csv_file.name}: {e}")
    
    print("\n" + "=" * 60)
    print("Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
