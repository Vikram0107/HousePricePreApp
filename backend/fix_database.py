import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'predictions.db')

def fix_database():
    """Completely fix database schema"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("="*60)
    print("FIXING DATABASE SCHEMA")
    print("="*60)
    
    # Check existing table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='predictions'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        # Get current columns
        cursor.execute("PRAGMA table_info(predictions)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"\nCurrent columns: {columns}")
        
        # List of required columns
        required_columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'timestamp': 'TEXT NOT NULL',
            'predicted_price': 'REAL NOT NULL',
            'formatted_price': 'TEXT NOT NULL',
            'confidence_lower': 'REAL NOT NULL',
            'confidence_upper': 'REAL NOT NULL',
            'formatted_lower': 'TEXT NOT NULL',
            'formatted_upper': 'TEXT NOT NULL',
            'all_features': 'TEXT',
            'input_features': 'TEXT',
            'vs_average_diff': 'TEXT',
            'vs_average_percent': 'TEXT',
            'actual_price': 'REAL',
            'is_verified': 'INTEGER DEFAULT 0',
            'added_to_training': 'INTEGER DEFAULT 0',
            'user_rating': 'INTEGER',
            'training_weight': 'REAL DEFAULT 0.8'
        }
        
        # Add missing columns
        for col_name, col_type in required_columns.items():
            if col_name not in columns and col_name != 'id':
                try:
                    cursor.execute(f"ALTER TABLE predictions ADD COLUMN {col_name} {col_type}")
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    print(f"⚠️ Could not add {col_name}: {e}")
        
        # Verify after additions
        cursor.execute("PRAGMA table_info(predictions)")
        updated_columns = [col[1] for col in cursor.fetchall()]
        print(f"\nUpdated columns: {updated_columns}")
        
    else:
        # Create fresh table
        print("\nCreating new predictions table...")
        cursor.execute('''
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                predicted_price REAL NOT NULL,
                formatted_price TEXT NOT NULL,
                confidence_lower REAL NOT NULL,
                confidence_upper REAL NOT NULL,
                formatted_lower TEXT NOT NULL,
                formatted_upper TEXT NOT NULL,
                all_features TEXT,
                input_features TEXT,
                vs_average_diff TEXT,
                vs_average_percent TEXT,
                actual_price REAL,
                is_verified INTEGER DEFAULT 0,
                added_to_training INTEGER DEFAULT 0,
                user_rating INTEGER,
                training_weight REAL DEFAULT 0.8
            )
        ''')
        print("✅ Created new predictions table")
    
    # Create training_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            prediction_id INTEGER,
            features TEXT NOT NULL,
            actual_price REAL NOT NULL,
            weight REAL DEFAULT 1.0,
            created_at TIMESTAMP,
            used_in_model INTEGER DEFAULT 0,
            model_version INTEGER
        )
    ''')
    print("✅ training_data table ready")
    
    # Create model_versions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS model_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            accuracy REAL,
            rmse REAL,
            mae REAL,
            trained_at TIMESTAMP,
            training_samples_original INTEGER,
            training_samples_user INTEGER,
            total_training_samples INTEGER,
            is_active INTEGER DEFAULT 1
        )
    ''')
    print("✅ model_versions table ready")
    
    # Create retraining_log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS retraining_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            triggered_by TEXT,
            new_predictions INTEGER,
            previous_model_version INTEGER,
            new_model_version INTEGER,
            accuracy_improvement REAL,
            trained_at TIMESTAMP
        )
    ''')
    print("✅ retraining_log table ready")
    
    conn.commit()
    
    # Final verification
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\n✅ All tables: {[t[0] for t in tables]}")
    
    cursor.execute("PRAGMA table_info(predictions)")
    final_columns = [col[1] for col in cursor.fetchall()]
    print(f"✅ Predictions table columns: {final_columns}")
    
    conn.close()
    print("\n" + "="*60)
    print("✅ DATABASE FIXED SUCCESSFULLY!")
    print("="*60)

if __name__ == '__main__':
    fix_database()