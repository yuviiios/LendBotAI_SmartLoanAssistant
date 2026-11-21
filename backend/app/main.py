import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.loan_routes import router as loan_router
from app.api.chat_routes import router as chat_router

from app.api.document_routes import router as document_router
from app.api.mock_routes import router as mock_router

app = FastAPI(title="Loan Processing System")

allowed_origin = os.getenv("ALLOWED_ORIGIN")
allowed_origins = [allowed_origin] if allowed_origin else []
if allowed_origin == "https://loan-chatbot-nine.vercel.app":
    # The deployed consultation is also accessible through these Vercel aliases.
    allowed_origins.extend([
        "https://loan-chatbot-git-main-yuviiios-projects.vercel.app",
        "https://loan-chatbot-ow58uhaiw-yuviiios-projects.vercel.app",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("app/static/outputs", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(document_router, prefix="/api")
app.include_router(mock_router, prefix="/api")
app.include_router(loan_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


# Render pings this to confirm the app is alive.
# Without it Render assumes the app is down and keeps restarting it.
@app.get("/health")
def health():
    return {"status": "ok"}
