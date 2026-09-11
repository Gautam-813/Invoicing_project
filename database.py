import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is missing or empty!")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Creates the invoices table in Supabase PostgreSQL if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            file_id TEXT NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            vendor VARCHAR(100) DEFAULT 'Pending Extraction',
            amount NUMERIC(10, 2) DEFAULT 0.0,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Supabase PostgreSQL initialized successfully.")