import streamlit as st
import sqlite3
import requests
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DB_NAME = "invoices.db"

st.set_page_config(page_title="Invoice Vault Dashboard", layout="wide", page_icon="🧾")

st.title("🧾 Invoice Vault Web Dashboard")
st.write("View and manage invoices uploaded via your Telegram Bot.")

def fetch_invoices():
    """Fetch all stored invoices from SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, file_id, file_type, vendor, amount, upload_date FROM invoices ORDER BY upload_date DESC")
    data = cursor.fetchall()
    conn.close()
    return data

def get_telegram_file_url(file_id):
    """Generates a direct download link for a Telegram file_id."""
    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
    if res.get("ok"):
        file_path = res["result"]["file_path"]
        return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    return None

# Fetch data
invoices = fetch_invoices()

if not invoices:
    st.info("No invoices found in the database. Upload some files through your Telegram Bot first!")
else:
    # Sidebar Filters
    st.sidebar.header("Filter & Search")
    search_query = st.sidebar.text_input("Search by ID or Vendor")

    # Display Summary Metric
    st.metric(label="Total Invoices Saved", value=len(invoices))

    # Convert to displayable format
    table_data = []
    for inv in invoices:
        inv_id, user_id, file_id, file_type, vendor, amount, upload_date = inv
        if search_query and (search_query.lower() not in str(inv_id) and search_query.lower() not in vendor.lower()):
            continue
        table_data.append({
            "ID": inv_id,
            "User ID": user_id,
            "File Type": file_type.capitalize(),
            "Vendor": vendor,
            "Amount": f"${amount:.2f}",
            "Upload Date": upload_date,
            "file_id": file_id
        })

    st.subheader("Invoice Records")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        selected_id = st.selectbox(
            "Select an Invoice ID to preview:", 
            options=[item["ID"] for item in table_data]
        )
        st.table(table_data)

    with col2:
        st.subheader("Invoice Preview")
        if selected_id:
            selected_item = next(item for item in table_data if item["ID"] == selected_id)
            with st.spinner("Fetching file from Telegram..."):
                file_url = get_telegram_file_url(selected_item["file_id"])

            if file_url:
                if selected_item["File Type"].lower() == "photo":
                    st.image(file_url, caption=f"Invoice #{selected_id}")
                else:
                    st.success("PDF Document Ready")
                    st.markdown(f"[📥 Download PDF Invoice]({file_url})")
            else:
                st.error("Failed to fetch file link from Telegram. Check if BOT_TOKEN is valid.")