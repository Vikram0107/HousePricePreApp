import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'predictions.db')

def update_database():
    """Update database schema to match new app.py requirements"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check existing columns in predictions table
    cursor.execute("PRAGMA table_info(predictions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    print("Current columns:", columns)
    
    # Add missing columns if they don't exist
    if 'all_features' not in columns:
        print("Adding all_features column...")
        cursor.execute("ALTER TABLE predictions ADD COLUMN all_features TEXT")
    
    if 'added_to_training' not in columns:
        print("Adding added_to_training column...")
        cursor.execute("ALTER TABLE predictions ADD COLUMN added_to_training INTEGER DEFAULT 0")
    
    if 'training_weight' not in columns:
        print("Adding training_weight column...")
        cursor.execute("ALTER TABLE predictions ADD COLUMN training_weight REAL DEFAULT 0.8")
    
    # Create training_data table if it doesn't exist
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
    
    # Create model_versions table if it doesn't exist
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
    
    # Create retraining_log table if it doesn't exist
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
    
    conn.commit()
    
    # Verify columns after update
    cursor.execute("PRAGMA table_info(predictions)")
    updated_columns = [column[1] for column in cursor.fetchall()]
    print("\nUpdated columns:", updated_columns)
    
    conn.close()
    print("\n✅ Database updated successfully!")

if __name__ == '__main__':
    update_database()