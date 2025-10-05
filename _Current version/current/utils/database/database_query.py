#!/usr/bin/env python3
"""
Database Query Utility - Query the indexed PatchIO database
Demonstrates how to query the SQLite database for search functionality.
"""

import sqlite3
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

class DatabaseQuery:
    """Query utility for the PatchIO indexed database"""
    
    def __init__(self, db_path: str = "patchio_index.db"):
        """Initialize the database query utility"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        self._connect()
    
    def _connect(self):
        """Connect to the database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")
            raise
    
    def search_files(self, 
                    query: str = "", 
                    file_types: List[str] = None,
                    vendors: List[str] = None,
                    libraries: List[str] = None,
                    instruments: List[str] = None,
                    genres: List[str] = None,
                    moods: List[str] = None,
                    formats: List[str] = None,
                    bpm: str = None,
                    key: str = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search files in the database
        
        Args:
            query: Text to search in file names and paths
            file_types: List of file types to filter by
            vendors: List of vendors to filter by
            libraries: List of libraries to filter by
            instruments: List of instruments to filter by
            genres: List of genres to filter by
            moods: List of moods to filter by
            formats: List of formats to filter by
            bpm: BPM filter (exact match)
            key: Musical key filter (exact match)
            limit: Maximum number of results
            
        Returns:
            List of file records matching the criteria
        """
        try:
            # Build the WHERE clause
            conditions = []
            params = []
            
            if query:
                conditions.append("(name LIKE ? OR path LIKE ? OR vendor LIKE ? OR library LIKE ? OR instrument LIKE ? OR genre LIKE ? OR mood LIKE ? OR format LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"])
            
            if file_types:
                placeholders = ','.join(['?' for _ in file_types])
                conditions.append(f"file_type IN ({placeholders})")
                params.extend(file_types)
            
            if vendors:
                placeholders = ','.join(['?' for _ in vendors])
                conditions.append(f"vendor IN ({placeholders})")
                params.extend(vendors)
            
            if libraries:
                placeholders = ','.join(['?' for _ in libraries])
                conditions.append(f"library IN ({placeholders})")
                params.extend(libraries)
            
            if instruments:
                # Handle JSON arrays in instrument field
                instrument_conditions = []
                for instrument in instruments:
                    instrument_conditions.append("instrument LIKE ?")
                    params.append(f'%"{instrument}"%')
                conditions.append(f"({' OR '.join(instrument_conditions)})")
            
            if genres:
                # Handle JSON arrays in genre field
                genre_conditions = []
                for genre in genres:
                    genre_conditions.append("genre LIKE ?")
                    params.append(f'%"{genre}"%')
                conditions.append(f"({' OR '.join(genre_conditions)})")
            
            if moods:
                # Handle JSON arrays in mood field
                mood_conditions = []
                for mood in moods:
                    mood_conditions.append("mood LIKE ?")
                    params.append(f'%"{mood}"%')
                conditions.append(f"({' OR '.join(mood_conditions)})")
            
            if formats:
                # Handle JSON arrays in format field
                format_conditions = []
                for format in formats:
                    format_conditions.append("format LIKE ?")
                    params.append(f'%"{format}"%')
                conditions.append(f"({' OR '.join(format_conditions)})")
            
            if bpm:
                conditions.append("bpm = ?")
                params.append(bpm)
            
            if key:
                conditions.append("key = ?")
                params.append(key)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Execute query
            sql = f'''
                SELECT path, name, extension, file_type, parent_folder, 
                       modified_time, bpm, key, vendor, library, keywords, tags,
                       instrument, genre, mood, format
                FROM files 
                WHERE {where_clause}
                ORDER BY name
                LIMIT ?
            '''
            params.append(limit)
            
            self.cursor.execute(sql, params)
            results = self.cursor.fetchall()
            
            # Convert to list of dictionaries
            columns = ['path', 'name', 'extension', 'file_type', 'parent_folder',
                      'modified_time', 'bpm', 'key', 'vendor', 'library', 'keywords', 'tags',
                      'instrument', 'genre', 'mood', 'format']
            
            return [dict(zip(columns, row)) for row in results]
            
        except Exception as e:
            print(f"❌ Error searching files: {e}")
            return []
    
    def get_vendors(self) -> List[str]:
        """Get all unique vendors in the database"""
        try:
            self.cursor.execute('''
                SELECT DISTINCT vendor 
                FROM files 
                WHERE vendor IS NOT NULL AND vendor != ''
                ORDER BY vendor
            ''')
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"❌ Error getting vendors: {e}")
            return []
    
    def get_libraries(self) -> List[str]:
        """Get all unique libraries in the database"""
        try:
            self.cursor.execute('''
                SELECT DISTINCT library 
                FROM files 
                WHERE library IS NOT NULL AND library != ''
                ORDER BY library
            ''')
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"❌ Error getting libraries: {e}")
            return []
    
    def get_file_types(self) -> List[str]:
        """Get all unique file types in the database"""
        try:
            self.cursor.execute('''
                SELECT DISTINCT file_type 
                FROM files 
                WHERE file_type IS NOT NULL
                ORDER BY file_type
            ''')
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"❌ Error getting file types: {e}")
            return []
    
    def get_instruments(self) -> List[str]:
        """Get all unique instruments in the database"""
        try:
            self.cursor.execute('''
                SELECT instrument 
                FROM files 
                WHERE instrument IS NOT NULL AND instrument != ''
            ''')
            instruments = set()
            for row in self.cursor.fetchall():
                try:
                    # Parse JSON array
                    instrument_list = json.loads(row[0]) if row[0] else []
                    instruments.update(instrument_list)
                except (json.JSONDecodeError, TypeError):
                    # Handle legacy single values
                    if row[0]:
                        instruments.add(row[0])
            return sorted(list(instruments))
        except Exception as e:
            print(f"❌ Error getting instruments: {e}")
            return []
    
    def get_genres(self) -> List[str]:
        """Get all unique genres in the database"""
        try:
            self.cursor.execute('''
                SELECT genre 
                FROM files 
                WHERE genre IS NOT NULL AND genre != ''
            ''')
            genres = set()
            for row in self.cursor.fetchall():
                try:
                    # Parse JSON array
                    genre_list = json.loads(row[0]) if row[0] else []
                    genres.update(genre_list)
                except (json.JSONDecodeError, TypeError):
                    # Handle legacy single values
                    if row[0]:
                        genres.add(row[0])
            return sorted(list(genres))
        except Exception as e:
            print(f"❌ Error getting genres: {e}")
            return []
    
    def get_moods(self) -> List[str]:
        """Get all unique moods in the database"""
        try:
            self.cursor.execute('''
                SELECT mood 
                FROM files 
                WHERE mood IS NOT NULL AND mood != ''
            ''')
            moods = set()
            for row in self.cursor.fetchall():
                try:
                    # Parse JSON array
                    mood_list = json.loads(row[0]) if row[0] else []
                    moods.update(mood_list)
                except (json.JSONDecodeError, TypeError):
                    # Handle legacy single values
                    if row[0]:
                        moods.add(row[0])
            return sorted(list(moods))
        except Exception as e:
            print(f"❌ Error getting moods: {e}")
            return []
    
    def get_formats(self) -> List[str]:
        """Get all unique formats in the database"""
        try:
            self.cursor.execute('''
                SELECT format 
                FROM files 
                WHERE format IS NOT NULL AND format != ''
            ''')
            formats = set()
            for row in self.cursor.fetchall():
                try:
                    # Parse JSON array
                    format_list = json.loads(row[0]) if row[0] else []
                    formats.update(format_list)
                except (json.JSONDecodeError, TypeError):
                    # Handle legacy single values
                    if row[0]:
                        formats.add(row[0])
            return sorted(list(formats))
        except Exception as e:
            print(f"❌ Error getting formats: {e}")
            return []
    
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get overall database statistics"""
        try:
            # Total files
            self.cursor.execute('SELECT COUNT(*) FROM files')
            total_files = self.cursor.fetchone()[0]
            
            # Files by type
            self.cursor.execute('''
                SELECT file_type, COUNT(*) as count 
                FROM files 
                GROUP BY file_type
                ORDER BY count DESC
            ''')
            files_by_type = dict(self.cursor.fetchall())
            
            # Top libraries
            self.cursor.execute('''
                SELECT library, COUNT(*) as count 
                FROM files 
                WHERE library IS NOT NULL AND library != ''
                GROUP BY library
                ORDER BY count DESC
                LIMIT 10
            ''')
            top_libraries = dict(self.cursor.fetchall())
            
            # Database size
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            return {
                'total_files': total_files,
                'files_by_type': files_by_type,
                'top_libraries': top_libraries,
                'database_size_bytes': db_size,
                'database_path': self.db_path
            }
            
        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def demo_queries():
    """Demonstrate various database queries"""
    try:
        query = DatabaseQuery("patchio_index.db")
        
        print("🔍 PatchIO Database Query Demo")
        print("=" * 50)
        
        # Get database statistics
        print("\n📊 Database Statistics:")
        stats = query.get_database_stats()
        for key, value in stats.items():
            if key in ['files_by_type', 'top_libraries']:
                print(f"  {key}:")
                for item, count in value.items():
                    print(f"    {item}: {count}")
            else:
                print(f"  {key}: {value}")
        
        # Get available file types
        print("\n📄 Available File Types:")
        file_types = query.get_file_types()
        for file_type in file_types:
            print(f"  - {file_type}")
        
        # Get available libraries
        print("\n📚 Available Libraries:")
        libraries = query.get_libraries()
        for library in libraries[:10]:  # Show first 10
            print(f"  - {library}")
        if len(libraries) > 10:
            print(f"  ... and {len(libraries) - 10} more")
        
        # Search examples
        print("\n🔍 Search Examples:")
        
        # Search for audio files
        audio_files = query.search_files(file_types=['Audio'], limit=5)
        print(f"  Audio files (first 5): {len(audio_files)} found")
        for file in audio_files:
            print(f"    - {file['name']} ({file['library']})")
        
        # Search for Kontakt files
        kontakt_files = query.search_files(file_types=['Kontakt'], limit=5)
        print(f"  Kontakt files (first 5): {len(kontakt_files)} found")
        for file in kontakt_files:
            print(f"    - {file['name']} ({file['library']})")
        
        # Search by BPM
        bpm_files = query.search_files(bpm="120bpm", limit=5)
        print(f"  120 BPM files: {len(bpm_files)} found")
        for file in bpm_files:
            print(f"    - {file['name']} ({file['bpm']})")
        
        query.close()
        
    except FileNotFoundError:
        print("❌ Database not found. Please run the indexer first to create the database.")
    except Exception as e:
        print(f"❌ Demo failed: {e}")


if __name__ == "__main__":
    demo_queries() 