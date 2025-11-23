import sqlite3
import sys

try:
    db = sqlite3.connect('economy.db')
    cursor = db.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("DATABASE STRUCTURE CHECK:")
    print("=" * 60)
    
    for table_name in tables:
        table = table_name[0]
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]
        
        print(f"\n📋 TABLE: {table}")
        print(f"   Columns: {', '.join(col_names)}")
        has_id = 'id' in col_names
        print(f"   Has 'id': {'✓' if has_id else '✗'}")
        
    db.close()
    print("\n" + "=" * 60)
    print("✅ Database check complete")
except Exception as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    sys.exit(1)
