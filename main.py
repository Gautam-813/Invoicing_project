import os
import threading
from datetime import datetime, date
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

import database
import bot

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB + start bot in background
    database.init_db()
    bot_thread = threading.Thread(target=bot.run_bot, daemon=True)
    bot_thread.start()
    print("Bot started in background thread.")
    yield
    # Shutdown (nothing needed)


app = FastAPI(title="Invoice Vault", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


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

    file_id = target[3] if len(target) > 3 else None
    if not file_id:
        return JSONResponse(content={"error": "No file_id"}, status_code=404)

    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
    if res.get("ok"):
        file_path = res["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        return JSONResponse(content={"url": url})

    return JSONResponse(content={"error": "Failed to get file from Telegram"}, status_code=500)
