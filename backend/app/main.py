from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import chat, upload, documents

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BalanceSheet Chat Backend (Gemini)")


# CORS (allow all during dev – tighten for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(documents.router, prefix="", tags=["documents"])


@app.get("/health")
def health():
    return {"status": "ok"}
