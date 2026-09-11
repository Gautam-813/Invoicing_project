import os
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, Request, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

import database

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEFAULT_CHAT_ID = os.getenv("DEFAULT_CHAT_ID")


async def start_bot_polling():
    """Start the Telegram bot using async polling (runs alongside FastAPI)."""
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

    import bot as bot_module

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", bot_module.start))
    application.add_handler(CommandHandler("list", bot_module.list_invoices))
    application.add_handler(CommandHandler("get", bot_module.get_invoice))
    application.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.ALL, bot_module.handle_document_or_photo)
    )

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("Bot polling started.")

    # Keep running until shutdown
    await asyncio.Event().wait()


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()

    bot_task = asyncio.create_task(start_bot_polling())
    print("Bot task created.")
    yield
    bot_task.cancel()


app = FastAPI(title="Invoice Vault", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/health")
async def health():
    return JSONResponse(content={"status": "ok"})


@app.get("/api/invoices")
async def api_invoices(
    start_date: str = Query(None),
    end_date: str = Query(None),
    search: str = Query(None),
):
    sd = None
    ed = None

    if start_date:
        try:
            sd = datetime.combine(datetime.strptime(start_date, "%Y-%m-%d").date(), datetime.min.time())
        except ValueError:
            pass

    if end_date:
        try:
            ed = datetime.combine(datetime.strptime(end_date, "%Y-%m-%d").date(), datetime.max.time())
        except ValueError:
            pass

    rows = database.get_all_invoices(start_date=sd, end_date=ed)

    results = []
    for row in rows:
        inv_id, user_id, file_id, file_type, vendor, amount, upload_date = row
        if search:
            q = search.lower()
            if q not in str(inv_id) and q not in (vendor or "").lower():
                continue
        results.append({
            "id": inv_id,
            "user_id": user_id,
            "file_id": file_id,
            "file_type": file_type,
            "vendor": vendor or "Unknown",
            "amount": float(amount) if amount else 0.0,
            "upload_date": upload_date.strftime("%Y-%m-%d %H:%M") if upload_date else None,
        })

    return JSONResponse(content=results)


@app.get("/api/invoices/{invoice_id}/file-url")
async def api_invoice_file_url(invoice_id: int):
    rows = database.get_all_invoices()
    target = next((r for r in rows if r[0] == invoice_id), None)
    if not target:
        return JSONResponse(content={"error": "Invoice not found"}, status_code=404)

    file_id = target[2] if len(target) > 2 else None
    if not file_id:
        return JSONResponse(content={"error": "No file_id"}, status_code=404)

    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
    if res.get("ok"):
        file_path = res["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        return JSONResponse(content={"url": url})

    return JSONResponse(content={"error": "Failed to get file from Telegram"}, status_code=500)


@app.post("/api/upload")
async def api_upload(
    file: UploadFile = File(...),
    vendor: str = Form("Pending Extraction"),
    amount: float = Form(0.0),
):
    if not DEFAULT_CHAT_ID:
        return JSONResponse(content={"error": "DEFAULT_CHAT_ID not configured on server"}, status_code=500)

    chat_id = DEFAULT_CHAT_ID.strip()

    # Determine file type and Telegram endpoint
    is_photo = file.content_type and file.content_type.startswith("image/")
    telegram_endpoint = "sendPhoto" if is_photo else "sendDocument"
    field_name = "photo" if is_photo else "document"

    # Read file content
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        return JSONResponse(content={"error": "File too large (max 10MB)"}, status_code=400)

    # Send to Telegram
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{telegram_endpoint}"
    files = {field_name: (file.filename, content, file.content_type or "application/octet-stream")}
    data = {"chat_id": chat_id}

    try:
        res = requests.post(url, data=data, files=files, timeout=30).json()
    except Exception as e:
        return JSONResponse(content={"error": f"Telegram API error: {str(e)}"}, status_code=500)

    if not res.get("ok"):
        error_msg = res.get("description", "Unknown error")
        return JSONResponse(content={"error": f"Telegram rejected: {error_msg}"}, status_code=400)

    # Extract file_id from Telegram response
    msg = res.get("result", {})
    file_id = None
    if is_photo:
        photos = msg.get("photo", [])
        if photos:
            file_id = photos[-1].get("file_id")
    else:
        doc = msg.get("document", {})
        file_id = doc.get("file_id")

    if not file_id:
        return JSONResponse(content={"error": "Could not extract file_id from Telegram"}, status_code=500)

    # Save to database
    file_type = "photo" if is_photo else "document"
    database.save_invoice(
        user_id=int(chat_id),
        file_id=file_id,
        file_type=file_type,
        vendor=vendor if vendor.strip() else "Pending Extraction",
        amount=amount if amount > 0 else 0.0,
    )

    return JSONResponse(content={
        "success": True,
        "file_id": file_id,
        "file_type": file_type,
    })
