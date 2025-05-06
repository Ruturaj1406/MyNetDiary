import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

# Database path
db_path = 'C:\\Users\\rutur\\mynetdiary_project\\tracker.db'

# Ensure database file exists and is writable
try:
    if not os.path.exists(db_path):
        open(db_path, 'a').close()
        print(f"Created database file at {db_path}")
    os.chmod(db_path, 0o666)
    print(f"Set permissions on {db_path}")
except Exception as e:
    print(f"Failed to set up database file: {e}")
    exit(1)

# Connect to the database
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
except Exception as e:
    print(f"Failed to connect to database: {e}")
    exit(1)

# Drop and recreate the user table to ensure correct schema
try:
    cursor.execute('DROP TABLE IF EXISTS user')
    cursor.execute('''
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            sex TEXT,
            dob TEXT,
            height REAL,
            weight REAL,
            target_weight REAL,
            activity_level TEXT,
            dietary_pref TEXT,
            health_goal TEXT
        )
    ''')
    conn.commit()
    print("User table recreated with correct schema")
except Exception as e:
    print(f"Failed to recreate user table: {e}")
    conn.close()
    exit(1)

# Create or update user 'ruturajff'
username = 'ruturajff'
password = 'password123'  # Default password; change after logging in
try:
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    cursor.execute('''
        INSERT OR REPLACE INTO user (
            id, username, password, sex, dob, height, weight, target_weight,
            activity_level, dietary_pref, health_goal
        ) VALUES (
            (SELECT id FROM user WHERE username = ?),
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    ''', (
        username, username, hashed_password, 'male', '1990-01-01',
        170.0, 70.0, 65.0, 'moderate', 'vegetarian', 'loss'
    ))
    conn.commit()
    print(f"User '{username}' created/updated with hashed password")
except Exception as e:
    print(f"Failed to insert user: {e}")
    conn.close()
    exit(1)

# Verify user table schema
try:
    cursor.execute("PRAGMA table_info(user)")
    columns = [info[1] for info in cursor.fetchall()]
    expected_columns = [
        'id', 'username', 'password', 'sex', 'dob', 'height', 'weight',
        'target_weight', 'activity_level', 'dietary_pref', 'health_goal'
    ]
    if set(columns) == set(expected_columns):
        print("User table schema verified: all expected columns present")
    else:
        print(f"User table schema mismatch. Found: {columns}")
        conn.close()
        exit(1)
except Exception as e:
    print(f"Failed to verify user table schema: {e}")
    conn.close()
    exit(1)

# Verify user data
try:
    cursor.execute('SELECT username, password, sex, dob, height, weight, target_weight, activity_level, dietary_pref, health_goal FROM user WHERE username = ?', (username,))
    user_data = cursor.fetchone()
    if user_data:
        print(f"User profile: {user_data}")
    else:
        print(f"User {username} not found after insertion.")
        conn.close()
        exit(1)
except Exception as e:
    print(f"Failed to verify user data: {e}")
    conn.close()
    exit(1)

# Verify food and exercise tables (no changes needed)
try:
    food_count = cursor.execute('SELECT COUNT(*) FROM food').fetchone()[0]
    exercise_count = cursor.execute('SELECT COUNT(*) FROM exercise').fetchone()[0]
    print(f"Food table: {food_count} entries")
    print(f"Exercise table: {exercise_count} entries")
    if food_count < 21 or exercise_count < 10:
        print("Warning: Food or exercise table has fewer entries than expected. Run app.py to reinitialize.")
except Exception as e:
    print(f"Failed to verify food/exercise tables: {e}")

# Close connection
conn.close()
print("Database fix completed")