import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is missing!")
    
    db_url = db_url.strip().strip('"').strip("'")
    
    if db_url.startswith("DATABASE_URL="):
        db_url = db_url.split("DATABASE_URL=", 1)[1].strip()

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(dsn=db_url)


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


def save_invoice(user_id, file_id, file_type, vendor="Pending Extraction", amount=0.0):
    """Insert a new invoice record into the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO invoices (user_id, file_id, file_type, vendor, amount) VALUES (%s, %s, %s, %s, %s)",
        (user_id, file_id, file_type, vendor, amount)
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_user_invoices(user_id):
    """Fetch all invoices for a specific user, ordered by newest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, file_id, file_type, vendor, amount, upload_date FROM invoices WHERE user_id = %s ORDER BY upload_date DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_all_invoices(start_date=None, end_date=None):
    """Fetch all invoices, optionally filtered by date range."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT id, user_id, file_id, file_type, vendor, amount, upload_date FROM invoices"
    params = []
    conditions = []

    if start_date:
        conditions.append("upload_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("upload_date <= %s")
        params.append(end_date)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY upload_date DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows
