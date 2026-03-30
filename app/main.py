import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.routes.latest_news_routes import router as news_router
from app.routes.appointment_routes import router as appointment_router
from app.routes.issue_routes import router as issue_router
from app.routes.press_release_routes import router as press_release_router

ENV = os.environ.get("ENV", "production")

app = FastAPI(
    title="sammridhvarma",
    docs_url="/docs" if ENV == "development" else None,
    redoc_url="/redoc" if ENV == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception:
    pass

try:
    if engine:
        Base.metadata.create_all(bind=engine)
except Exception:
    pass

app.include_router(news_router)
app.include_router(appointment_router)
app.include_router(issue_router)
app.include_router(press_release_router)


@app.get("/health")
def health():
    return {"status": "ok"}
