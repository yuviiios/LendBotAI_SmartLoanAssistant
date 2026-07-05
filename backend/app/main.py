import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.loan_routes import router as loan_router
from app.api.chat_routes import router as chat_router

app = FastAPI(title="Loan Processing System")

allowed_origin = os.getenv("ALLOWED_ORIGIN")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("app/static/outputs", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(loan_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


# Render pings this to confirm the app is alive.
# Without it Render assumes the app is down and keeps restarting it.
@app.get("/health")
def health():
    return {"status": "ok"}