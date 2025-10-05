#!/usr/bin/env python3
"""
Vendor Maintenance Tool for PatchIO
Consolidated tool for AI-powered vendor identification and database synchronization.
Combines functionality from:
- ai_vendor_finder_optimized.py
- sync_knowledge_to_index.py  
- complete_vendor_update_workflow.py
"""

import sqlite3
import os
import json
import time
import argparse
import subprocess
import sys
import requests
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import openai
from pathlib import Path
from Crypto.Cipher import AES
import base64

# PatchIO API Key Configuration
API_KEY_FILE_ID = "1lBtKmwOXK6J8BySnecdrI6QSrFkCWETL"
AES_KEY = b'NahaPatchio12345'

# Cache API key
_cached_api_key = None

# Util: Unpad PKCS#7
def unpad(s):
    return s[:-ord(s[-1:])]

# Load & Decrypt API key from Google Drive
def load_encrypted_api_key_from_drive(file_id, aes_key):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        response = requests.get(url, timeout=10)
        encrypted_bytes = base64.b64decode(response.content)
        
        cipher = AES.new(aes_key, AES.MODE_ECB)
        decrypted = cipher.decrypt(encrypted_bytes)
        api_key = unpad(decrypted).decode("utf-8")
        return api_key
    except Exception as e:
        print(f"Error loading/decrypting API key: {e}")
        return None

# Cached access
def get_cached_api_key():
    global _cached_api_key
    if _cached_api_key is None:
        _cached_api_key = load_encrypted_api_key_from_drive(API_KEY_FILE_ID, AES_KEY)
    return _cached_api_key

@dataclass
class VendorLibraryInfo:
    """Information about a vendor/library combination"""
    library_name: str
    vendor_name: str
    confidence: float
    reasoning: str
    file_paths: List[str]

class AIVendorFinder:
    """AI-powered vendor identifier using batch processing"""
    
    def __init__(self, db_path: str, api_key: str = None, model: str = "gpt-3.5-turbo", require_api: bool = True):
        """Initialize the AI vendor finder"""
        self.db_path = db_path
        self.model = model
        
        # Initialize OpenAI client
        if api_key:
            openai.api_key = api_key
        elif os.getenv('OPENAI_API_KEY'):
            openai.api_key = os.getenv('OPENAI_API_KEY')
        elif require_api:
            cached_api_key = get_cached_api_key()
            if cached_api_key:
                openai.api_key = cached_api_key
                print("✅ Successfully loaded API key from Google Drive.")
            else:
                raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable, pass api_key parameter, or ensure Google Drive access.")
        
        # Connect to database
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        # Statistics
        self.stats = {
            'total_unknown': 0,
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'api_calls_made': 0,
            'estimated_cost': 0.0
        }
    
    def get_unknown_libraries(self) -> List[Tuple[str, int]]:
        """Get list of libraries with unknown vendors and their file counts"""
        query = '''
            SELECT library, COUNT(*) as file_count
            FROM files 
            WHERE vendor = 'Unknown Vendor' 
            AND library != 'Unknown Library'
            GROUP BY library
            ORDER BY file_count DESC
        '''
        
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def get_sample_paths_for_library(self, library_name: str, limit: int = 3) -> List[str]:
        """Get sample file paths for a library to help with identification"""
        query = '''
            SELECT path 
            FROM files 
            WHERE library = ? 
            AND vendor = 'Unknown Vendor'
            LIMIT ?
        '''
        
        self.cursor.execute(query, (library_name, limit))
        return [row[0] for row in self.cursor.fetchall()]
    
    def group_libraries_by_similarity(self, libraries: List[Tuple[str, int]], batch_size: int = 10) -> List[List[Tuple[str, int]]]:
        """Group libraries that might be from the same vendor for batch processing"""
        groups = []
        current_group = []
        
        for library_name, file_count in libraries:
            current_group.append((library_name, file_count))
            
            if len(current_group) >= batch_size:
                groups.append(current_group)
                current_group = []
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def ask_chatgpt_for_vendors_batch(self, library_batch: List[Tuple[str, int]]) -> Dict[str, VendorLibraryInfo]:
        """Ask ChatGPT to identify vendors for multiple libraries at once"""
        
        libraries_info = []
        for library_name, file_count in library_batch:
            sample_paths = self.get_sample_paths_for_library(library_name, limit=2)
            libraries_info.append({
                'name': library_name,
                'file_count': file_count,
                'sample_paths': sample_paths[:2]
            })
        
        prompt = f"""
You are a music production expert with extensive knowledge of sample libraries and music software vendors.

I need you to identify the VENDOR (company/publisher) for these sample libraries:

{json.dumps(libraries_info, indent=2)}

Please respond with ONLY a JSON object in this exact format:
{{
    "results": [
        {{
            "library": "Library Name",
            "vendor": "Exact Vendor Name",
            "confidence": 0.95,
            "reasoning": "Brief explanation"
        }}
    ]
}}

Rules:
1. Be very specific with vendor names (e.g., "Native Instruments", not just "Native")
2. Confidence should be 0.0-1.0 (1.0 = completely certain)
3. Only include results where confidence >= 0.7
4. If you're not confident about a library, don't include it in results
5. Consider the file paths - they often contain vendor information
6. Common vendors include: Native Instruments, Spitfire Audio, Heavyocity, Cinesamples, EastWest, Audio Imperia, Output, etc.
"""

        try:
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a music production expert specializing in sample libraries and music software vendors."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            self.stats['api_calls_made'] += 1
            
            # Estimate cost
            if self.model == "gpt-4":
                self.stats['estimated_cost'] += 0.02
            else:
                self.stats['estimated_cost'] += 0.002
            
            response_text = response.choices[0].message.content.strip()
            
            try:
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                result = json.loads(response_text)
                vendor_infos = {}
                
                for item in result.get("results", []):
                    if item.get("vendor") and item.get("confidence", 0) >= 0.7:
                        library_name = item["library"]
                        vendor_infos[library_name] = VendorLibraryInfo(
                            library_name=library_name,
                            vendor_name=item["vendor"],
                            confidence=item["confidence"],
                            reasoning=item["reasoning"],
                            file_paths=self.get_sample_paths_for_library(library_name)
                        )
                
                return vendor_infos
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse ChatGPT response: {e}")
                print(f"Response: {response_text}")
                return {}
                
        except Exception as e:
            print(f"❌ ChatGPT API error: {e}")
            return {}
    
    def update_database(self, vendor_info: VendorLibraryInfo) -> bool:
        """Update the database with the identified vendor information"""
        try:
            update_query = '''
                UPDATE files 
                SET vendor = ? 
                WHERE library = ? 
                AND vendor = 'Unknown Vendor'
            '''
            
            self.cursor.execute(update_query, (vendor_info.vendor_name, vendor_info.library_name))
            updated_count = self.cursor.rowcount
            
            self.conn.commit()
            
            print(f"✅ Updated {updated_count} files: {vendor_info.library_name} → {vendor_info.vendor_name}")
            return True
            
        except Exception as e:
            print(f"❌ Database update error for {vendor_info.library_name}: {e}")
            self.conn.rollback()
            return False
    
    def create_backup(self) -> str:
        """Create a backup of the database before making changes"""
        backup_path = f"{self.db_path}.backup_{int(time.time())}"
        
        try:
            backup_conn = sqlite3.connect(backup_path)
            self.conn.backup(backup_conn)
            backup_conn.close()
            
            print(f"💾 Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            print(f"❌ Backup creation failed: {e}")
            raise
    
    def process_libraries_optimized(self, batch_size: int = 10, dry_run: bool = False) -> Dict:
        """Process unknown libraries using optimized batch processing"""
        
        print("🔍 Finding unknown libraries...")
        unknown_libraries = self.get_unknown_libraries()
        
        if not unknown_libraries:
            print("✅ No unknown libraries found!")
            return self.stats
        
        self.stats['total_unknown'] = len(unknown_libraries)
        
        print(f"📊 Processing {len(unknown_libraries)} unknown libraries in batches of {batch_size}")
        
        if dry_run:
            print("🧪 DRY RUN MODE - No changes will be made to the database")
        
        if not dry_run:
            self.create_backup()
        
        library_groups = self.group_libraries_by_similarity(unknown_libraries, batch_size)
        
        print(f"\n🚀 Starting optimized AI vendor identification...")
        print(f"📦 Processing {len(library_groups)} batches (vs {len(unknown_libraries)} individual calls)")
        print("=" * 60)
        
        for batch_num, library_batch in enumerate(library_groups, 1):
            print(f"\n[Batch {batch_num}/{len(library_groups)}] Processing {len(library_batch)} libraries:")
            for library_name, file_count in library_batch:
                print(f"  - {library_name} ({file_count} files)")
            
            vendor_infos = self.ask_chatgpt_for_vendors_batch(library_batch)
            
            for library_name, file_count in library_batch:
                if library_name in vendor_infos:
                    vendor_info = vendor_infos[library_name]
                    print(f"🎯 {library_name} → {vendor_info.vendor_name} (confidence: {vendor_info.confidence:.2f})")
                    print(f"💭 {vendor_info.reasoning}")
                    
                    if not dry_run:
                        if self.update_database(vendor_info):
                            self.stats['successful'] += 1
                        else:
                            self.stats['failed'] += 1
                    else:
                        print("🧪 [DRY RUN] Would update database")
                        self.stats['successful'] += 1
                else:
                    print(f"❌ {library_name} → Could not identify vendor")
                    self.stats['failed'] += 1
                
                self.stats['processed'] += 1
            
            time.sleep(1)
        
        return self.stats
    
    def print_statistics(self):
        """Print processing statistics"""
        print("\n" + "=" * 60)
        print("📊 AI VENDOR FINDER STATISTICS")
        print("=" * 60)
        print(f"Total unknown libraries: {self.stats['total_unknown']}")
        print(f"Processed: {self.stats['processed']}")
        print(f"Successfully identified: {self.stats['successful']}")
        print(f"Failed to identify: {self.stats['failed']}")
        print(f"Success rate: {(self.stats['successful'] / max(self.stats['processed'], 1)) * 100:.1f}%")
        print(f"API calls made: {self.stats['api_calls_made']}")
        print(f"Estimated cost: ${self.stats['estimated_cost']:.3f}")
        print(f"Cost per library: ${self.stats['estimated_cost'] / max(self.stats['processed'], 1):.4f}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

class KnowledgeToIndexSync:
    """Sync vendor/library information from knowledge database to index database"""
    
    def __init__(self, knowledge_db_path: str, index_db_path: str):
        """Initialize the sync system"""
        self.knowledge_db_path = knowledge_db_path
        self.index_db_path = index_db_path
        
        # Connect to databases
        self.knowledge_conn = sqlite3.connect(knowledge_db_path)
        self.knowledge_cursor = self.knowledge_conn.cursor()
        
        self.index_conn = sqlite3.connect(index_db_path)
        self.index_cursor = self.index_conn.cursor()
        
        # Statistics
        self.stats = {
            'total_mappings': 0,
            'updated_files': 0,
            'libraries_processed': 0
        }
    
    def get_vendor_library_mappings(self) -> List[Tuple[str, str]]:
        """Get all vendor/library mappings from knowledge database"""
        query = '''
            SELECT DISTINCT vendor_name, library_name
            FROM vendor_library_mappings
            ORDER BY vendor_name, library_name
        '''
        
        self.knowledge_cursor.execute(query)
        return self.knowledge_cursor.fetchall()
    
    def update_index_database(self, vendor: str, library: str) -> int:
        """Update vendor information for a library in the index database"""
        try:
            update_query = '''
                UPDATE files 
                SET vendor = ? 
                WHERE library = ? 
                AND (vendor = 'Unknown Vendor' OR vendor IS NULL)
            '''
            
            self.index_cursor.execute(update_query, (vendor, library))
            updated_count = self.index_cursor.rowcount
            
            self.index_conn.commit()
            return updated_count
            
        except Exception as e:
            print(f"❌ Error updating {library} → {vendor}: {e}")
            self.index_conn.rollback()
            return 0
    
    def sync_knowledge_to_index(self, dry_run: bool = False) -> Dict:
        """Sync vendor/library mappings from knowledge database to index database"""
        
        print("🔍 Getting vendor/library mappings from knowledge database...")
        vendor_library_mappings = self.get_vendor_library_mappings()
        
        if not vendor_library_mappings:
            print("❌ No vendor/library mappings found in knowledge database!")
            return self.stats
        
        self.stats['total_mappings'] = len(vendor_library_mappings)
        
        print(f"📊 Found {len(vendor_library_mappings)} vendor/library mappings")
        
        if dry_run:
            print("🧪 DRY RUN MODE - No changes will be made to the index database")
        
        print("\n🚀 Syncing vendor/library information...")
        print("=" * 60)
        
        for vendor, library in vendor_library_mappings:
            print(f"📝 Processing: {library} → {vendor}")
            
            if not dry_run:
                updated_count = self.update_index_database(vendor, library)
                if updated_count > 0:
                    print(f"✅ Updated {updated_count} files: {library} → {vendor}")
                    self.stats['updated_files'] += updated_count
                else:
                    print(f"ℹ️ No files to update for {library}")
            else:
                self.index_cursor.execute('''
                    SELECT COUNT(*) FROM files 
                    WHERE library = ? 
                    AND (vendor = 'Unknown Vendor' OR vendor IS NULL)
                ''', (library,))
                would_update = self.index_cursor.fetchone()[0]
                print(f"🧪 [DRY RUN] Would update {would_update} files: {library} → {vendor}")
                self.stats['updated_files'] += would_update
            
            self.stats['libraries_processed'] += 1
        
        return self.stats
    
    def print_statistics(self):
        """Print sync statistics"""
        print("\n" + "=" * 60)
        print("📊 SYNC STATISTICS")
        print("=" * 60)
        print(f"Total mappings in knowledge DB: {self.stats['total_mappings']}")
        print(f"Libraries processed: {self.stats['libraries_processed']}")
        print(f"Files updated in index DB: {self.stats['updated_files']}")
    
    def close(self):
        """Close database connections"""
        if self.knowledge_conn:
            self.knowledge_conn.close()
        if self.index_conn:
            self.index_conn.close()

class VendorMaintenanceWorkflow:
    """Complete workflow for vendor maintenance operations"""
    
    def __init__(self, knowledge_db_path: str, index_db_path: str):
        """Initialize the workflow"""
        self.knowledge_db_path = knowledge_db_path
        self.index_db_path = index_db_path
        
        # Statistics
        self.stats = {
            'unknown_libraries_before': 0,
            'unknown_libraries_after': 0,
            'ai_identifications': 0,
            'knowledge_db_updates': 0,
            'index_db_updates': 0,
            'total_cost': 0.0
        }
    
    def get_unknown_libraries_count(self) -> int:
        """Get count of libraries with unknown vendors"""
        conn = sqlite3.connect(self.index_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(DISTINCT library)
            FROM files 
            WHERE vendor = 'Unknown Vendor' 
            AND library != 'Unknown Library'
        ''')
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def run_ai_vendor_finder(self, dry_run: bool = False) -> Dict:
        """Run the AI vendor finder on index database"""
        print("🤖 Step 1: Running AI Vendor Finder...")
        print("=" * 60)
        
        try:
            finder = AIVendorFinder(
                db_path=self.index_db_path,
                model="gpt-3.5-turbo",
                require_api=not dry_run
            )
            
            stats = finder.process_libraries_optimized(batch_size=10, dry_run=dry_run)
            finder.print_statistics()
            finder.close()
            
            self.stats['ai_identifications'] = stats['successful']
            self.stats['total_cost'] = stats['estimated_cost']
            
            return {"success": True, "stats": stats}
                
        except Exception as e:
            print(f"❌ Error running AI Vendor Finder: {e}")
            return {"success": False, "error": str(e)}
    
    def run_knowledge_sync(self, dry_run: bool = False) -> Dict:
        """Run the knowledge database to index database sync"""
        print("\n🔄 Step 2: Syncing Knowledge Database to Index Database...")
        print("=" * 60)
        
        try:
            sync = KnowledgeToIndexSync(self.knowledge_db_path, self.index_db_path)
            stats = sync.sync_knowledge_to_index(dry_run=dry_run)
            sync.print_statistics()
            sync.close()
            
            self.stats['index_db_updates'] = stats['updated_files']
            
            return {"success": True, "stats": stats}
                
        except Exception as e:
            print(f"❌ Error running knowledge sync: {e}")
            return {"success": False, "error": str(e)}
    
    def run_complete_workflow(self, dry_run: bool = False) -> Dict:
        """Run the complete vendor maintenance workflow"""
        print("🚀 Complete Vendor Maintenance Workflow")
        print("=" * 60)
        
        # Get initial statistics
        self.stats['unknown_libraries_before'] = self.get_unknown_libraries_count()
        
        print(f"📊 Initial State:")
        print(f"  - Libraries with unknown vendors: {self.stats['unknown_libraries_before']}")
        
        if dry_run:
            print("\n🧪 DRY RUN MODE - No changes will be made")
        
        # Step 1: AI Vendor Finder
        ai_result = self.run_ai_vendor_finder(dry_run)
        if not ai_result["success"]:
            return {"success": False, "error": "AI Vendor Finder failed", "details": ai_result}
        
        # Step 2: Knowledge Sync
        sync_result = self.run_knowledge_sync(dry_run)
        if not sync_result["success"]:
            return {"success": False, "error": "Knowledge sync failed", "details": sync_result}
        
        # Get final statistics
        self.stats['unknown_libraries_after'] = self.get_unknown_libraries_count()
        
        # Print final report
        self.print_final_report()
        
        return {"success": True, "stats": self.stats}
    
    def print_final_report(self):
        """Print comprehensive final report"""
        print("\n" + "=" * 60)
        print("📊 FINAL WORKFLOW REPORT")
        print("=" * 60)
        
        print(f"📈 Libraries with unknown vendors:")
        print(f"  - Before: {self.stats['unknown_libraries_before']}")
        print(f"  - After: {self.stats['unknown_libraries_after']}")
        print(f"  - Improvement: {self.stats['unknown_libraries_before'] - self.stats['unknown_libraries_after']} libraries identified")
        
        print(f"\n🤖 AI Processing:")
        print(f"  - Libraries identified by AI: {self.stats['ai_identifications']}")
        print(f"  - Index DB files updated: {self.stats['index_db_updates']}")
        print(f"  - Total cost: ${self.stats['total_cost']:.3f}")
        
        success_rate = (self.stats['ai_identifications'] / max(self.stats['unknown_libraries_before'], 1)) * 100
        print(f"\n📊 Success Rate: {success_rate:.1f}%")
        
        if self.stats['unknown_libraries_after'] == 0:
            print("\n🎉 SUCCESS: All libraries now have vendor information!")
        else:
            remaining = self.stats['unknown_libraries_after']
            print(f"\n⚠️ {remaining} libraries still need vendor identification")

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="Vendor Maintenance Tool for PatchIO")
    parser.add_argument("command", choices=["ai-find", "sync", "workflow"], 
                       help="Command to run: ai-find, sync, or workflow")
    parser.add_argument("knowledge_db", help="Path to the knowledge database file")
    parser.add_argument("index_db", help="Path to the index database file")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="OpenAI model to use")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for AI processing")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes, just show what would be done")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.knowledge_db):
        print(f"❌ Knowledge database file not found: {args.knowledge_db}")
        return 1
    
    if not os.path.exists(args.index_db):
        print(f"❌ Index database file not found: {args.index_db}")
        return 1
    
    try:
        if args.command == "ai-find":
            finder = AIVendorFinder(
                db_path=args.index_db,
                api_key=args.api_key,
                model=args.model,
                require_api=not args.dry_run
            )
            stats = finder.process_libraries_optimized(batch_size=args.batch_size, dry_run=args.dry_run)
            finder.print_statistics()
            finder.close()
            
        elif args.command == "sync":
            sync = KnowledgeToIndexSync(args.knowledge_db, args.index_db)
            stats = sync.sync_knowledge_to_index(dry_run=args.dry_run)
            sync.print_statistics()
            sync.close()
            
        elif args.command == "workflow":
            workflow = VendorMaintenanceWorkflow(args.knowledge_db, args.index_db)
            result = workflow.run_complete_workflow(dry_run=args.dry_run)
            
            if not result["success"]:
                print(f"\n❌ Workflow failed: {result['error']}")
                return 1
        
        print("\n✅ Operation completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
