import sqlite3
import os

# Get absolute path to db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "expenses.db")

# Connect to the database
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Create the budgets table
cur.execute('''
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        month TEXT NOT NULL
    )
''')

conn.commit()
conn.close()
