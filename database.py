import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Fetch Supabase connection URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
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

def save_invoice(user_id: int, file_id: str, file_type: str, vendor: str = "Pending Extraction", amount: float = 0.0):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO invoices (user_id, file_id, file_type, vendor, amount)
        VALUES (%s, %s, %s, %s, %s);
    """, (user_id, file_id, file_type, vendor, amount))
    
    conn.commit()
    cursor.close()
    conn.close()

def get_user_invoices(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, file_id, file_type, vendor, amount, upload_date 
        FROM invoices 
        WHERE user_id = %s
        ORDER BY upload_date DESC;
    """, (user_id,))
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_all_invoices():
    """Fetches all stored invoices across all users for the Streamlit Dashboard."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, user_id, file_id, file_type, vendor, amount, upload_date 
        FROM invoices 
        ORDER BY upload_date DESC;
    """)
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows