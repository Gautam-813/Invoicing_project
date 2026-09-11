import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes
)

import database

# Initialize Database
database.init_db()

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"Hello {user}! 👋 Send or upload any invoice (Photo or PDF Document) and I will save it for you.\n\n"
        "Commands:\n"
        "• /list - View all your saved invoices\n"
        "• /get <id> - Fetch and view a specific invoice (e.g. /get 1)"
    )

async def handle_document_or_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    else:
        return

    # Save record to SQLite
    database.save_invoice(
        user_id=user_id,
        file_id=file_id,
        file_type=file_type,
        vendor="Pending Extraction",
        amount=0.0
    )

    await update.message.reply_text(
        f"✅ Invoice saved successfully!\n\n"
        f"• File Type: {file_type.capitalize()}\n"
        f"• File ID: `{file_id[:15]}...`\n\n"
        f"Type /list to view all entries or /get to retrieve a file.",
        parse_mode="Markdown"
    )

async def list_invoices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    invoices = database.get_user_invoices(user_id)
    
    if not invoices:
        await update.message.reply_text("No invoices found.")
        return

    msg = "🧾 *Your Saved Invoices:*\n\n"
    for inv in invoices:
        inv_id, file_id, file_type, vendor, amount, upload_date = inv
        
        # Safely format datetime object or string
        date_str = upload_date.strftime("%Y-%m-%d") if hasattr(upload_date, 'strftime') else str(upload_date)[:10]
        
        msg += f"• *ID {inv_id}* | {date_str} | Type: {file_type} -> Use `/get {inv_id}`\n"

    await update.message.reply_text(msg, parse_mode="Markdown")
async def get_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Validate command argument
    if not context.args:
        await update.message.reply_text("Please provide an invoice ID. Example: `/get 1`", parse_mode="Markdown")
        return

    try:
        invoice_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid ID format. Use a number like `/get 1`.", parse_mode="Markdown")
        return

    invoices = database.get_user_invoices(user_id)
    target_invoice = next((inv for inv in invoices if inv[0] == invoice_id), None)

    if not target_invoice:
        await update.message.reply_text(f"❌ No invoice found with ID {invoice_id}.")
        return

    inv_id, file_id, file_type, vendor, amount, upload_date = target_invoice

    # Send file back using stored file_id
    if file_type == "photo":
        await update.message.reply_photo(photo=file_id, caption=f"📄 Invoice #{inv_id} ({upload_date[:10]})")
    else:
        await update.message.reply_document(document=file_id, caption=f"📄 Invoice #{inv_id} ({upload_date[:10]})")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_invoices))
    app.add_handler(CommandHandler("get", get_invoice))
    
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_document_or_photo))

    print("Bot running with full upload and retrieval logic...")
    app.run_polling()