"""
Database migration script.
Adds missing columns to existing tables without losing data.
Run once, then delete: python migrate.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'spice_bites.db')

# Each entry: (table, column, column_definition)
MIGRATIONS = [
    ('sale_bills', 'customer_id', 'INTEGER'),
    ('sale_bills', 'discount', 'REAL DEFAULT 0'),
    ('sale_bill_items', 'discount_percent', 'REAL DEFAULT 0'),
    ('batches', 'expiry_date', 'DATE'),
    ('payment_transactions', 'discount_amount', 'REAL DEFAULT 0'),
    ('sale_bills', 'customer_phone', 'VARCHAR(20) DEFAULT ""'),
]

def get_existing_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Also ensure the regular_customers table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regular_customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            address TEXT,
            phone VARCHAR(20),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    for table, column, col_def in MIGRATIONS:
        existing = get_existing_columns(cursor, table)
        if column not in existing:
            sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"
            print(f"  ✅ Adding {table}.{column}")
            cursor.execute(sql)
        else:
            print(f"  ⏭️  {table}.{column} already exists")
    
    conn.commit()
    conn.close()
    print("\n🎉 Migration complete!")

if __name__ == '__main__':
    migrate()
