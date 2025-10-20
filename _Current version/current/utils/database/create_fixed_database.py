#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Fixed Database: Duplicate your database with improved library extraction

This script:
1. Copies your original database to a new file (fixed_index.db)
2. Re-extracts vendor/library for all .nki files using the new extractor
3. Updates the fixed database with the improved values
4. Shows you statistics on what changed

Your original database stays COMPLETELY UNTOUCHED!
"""

import sys
import sqlite3
import shutil
import os
from pathlib import Path

# Add path for imports (we're already in the database directory)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from library_extractor_v3 import LibraryExtractorV3
from library_folder_mapper import TwoPassLibraryExtractor


def create_fixed_database():
    """
    Main function to create a fixed copy of the database
    """
    
    # Paths
    original_db = "/Users/shaked/Library/Application Support/PatchIO/patchio_index.db"
    fixed_db = "/Users/shaked/Library/Application Support/PatchIO/fixed_index.db"
    
    print("\n" + "="*80)
    print("🔧 CREATING FIXED DATABASE COPY")
    print("="*80 + "\n")
    
    # Check if original exists
    if not os.path.exists(original_db):
        print(f"❌ Original database not found: {original_db}")
        return
    
    # Step 1: Create a copy
    print(f"📋 Step 1: Copying original database...")
    print(f"   From: {original_db}")
    print(f"   To:   {fixed_db}")
    
    if os.path.exists(fixed_db):
        response = input(f"\n⚠️  {fixed_db} already exists. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled.")
            return
        os.remove(fixed_db)
    
    shutil.copy2(original_db, fixed_db)
    print(f"✅ Database copied!\n")
    
    # Step 2: Get all files from database
    print(f"🔍 Step 2: Loading all files from database...")
    conn = sqlite3.connect(fixed_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, path, vendor, library FROM files")
    all_files = cursor.fetchall()
    print(f"   Found {len(all_files):,} total files\n")
    
    # Step 3: Initialize Two-Pass extractor
    print(f"📚 Step 3: Initializing Two-Pass library extractor...")
    print(f"   This will:")
    print(f"   1. Build mapping from .nki files first")
    print(f"   2. Apply library names to .wav/.aiff files in same library")
    print(f"   (Your approach: .nki files determine library names!)\n")
    
    extractor = TwoPassLibraryExtractor()
    
    # Extract all file paths for initialization
    all_paths = [path for _, path, _, _ in all_files]
    
    # Initialize with all paths (builds .nki mapping)
    extractor.initialize(all_paths)
    
    print(f"✅ Two-Pass extractor ready!\n")
    
    # Step 4: Re-extract and update ALL files
    print(f"🔧 Step 4: Re-extracting library names for ALL files...")
    print(f"   .nki files: Direct extraction")
    print(f"   .wav/.aiff files: Inherit from .nki files in same library")
    print(f"   This may take a few minutes...\n")
    
    files = all_files  # Process all files
    
    stats = {
        'total': 0,
        'unchanged': 0,
        'improved': 0,
        'changed': 0,
        'improvements': []
    }
    
    # Process in batches for better performance
    batch_size = 100
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        
        for file_id, path, old_vendor, old_library in batch:
            stats['total'] += 1
            
            # Extract using Two-Pass system (.wav inherits from .nki)
            new_vendor, new_library = extractor.extract(path)
            
            # Compare
            if old_library == new_library and old_vendor == new_vendor:
                stats['unchanged'] += 1
            elif old_library == 'Unknown Library' and new_library != 'Unknown Library':
                stats['improved'] += 1
                stats['improvements'].append({
                    'path': path,
                    'old_vendor': old_vendor,
                    'old_library': old_library,
                    'new_vendor': new_vendor,
                    'new_library': new_library
                })
                # Update database
                cursor.execute(
                    "UPDATE files SET vendor = ?, library = ? WHERE id = ?",
                    (new_vendor, new_library, file_id)
                )
            else:
                stats['changed'] += 1
                # Update database
                cursor.execute(
                    "UPDATE files SET vendor = ?, library = ? WHERE id = ?",
                    (new_vendor, new_library, file_id)
                )
            
            # Progress indicator
            if stats['total'] % 500 == 0:
                progress = (stats['total'] / len(files)) * 100
                print(f"   Progress: {stats['total']:,}/{len(files):,} ({progress:.1f}%)")
    
    # Commit changes
    conn.commit()
    print(f"\n✅ All files processed!\n")
    
    # Step 5: Show statistics
    print("="*80)
    print("📊 RESULTS")
    print("="*80 + "\n")
    
    print(f"Total files processed: {stats['total']:,}")
    print(f"  ✅ Improved (Unknown → Known): {stats['improved']:,} files")
    print(f"  🔄 Changed: {stats['changed']:,} files")
    print(f"  ✓ Unchanged: {stats['unchanged']:,} files")
    print()
    
    # Show some improvements
    if stats['improvements']:
        print(f"🎉 IMPROVEMENTS (showing first 20):\n")
        for i, improvement in enumerate(stats['improvements'][:20], 1):
            print(f"{i}. ...{improvement['path'][-50:]}")
            print(f"   Before: {improvement['old_vendor']} / {improvement['old_library']}")
            print(f"   After:  {improvement['new_vendor']} / {improvement['new_library']}")
            print()
    
    # Final summary
    print("="*80)
    print("✅ FIXED DATABASE CREATED!")
    print("="*80 + "\n")
    
    print(f"📁 Original database (UNTOUCHED):")
    print(f"   {original_db}")
    print()
    print(f"📁 Fixed database (with improvements):")
    print(f"   {fixed_db}")
    print()
    print(f"💡 Next steps:")
    print(f"   1. Review the changes above")
    print(f"   2. Compare the databases if needed")
    print(f"   3. If satisfied, you can:")
    print(f"      - Use fixed_index.db as your new database")
    print(f"      - Or integrate the new extractor into PatchIO")
    print()
    
    conn.close()


if __name__ == "__main__":
    try:
        create_fixed_database()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

