import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.database import Base, engine
from app.routes import press_release_routes, appointment_routes, issue_routes, latest_news_routes

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

try:
    if engine is not None:
        Base.metadata.create_all(bind=engine)
except Exception:
    pass


app.include_router(press_release_routes.router)
app.include_router(appointment_routes.router)
app.include_router(issue_routes.router)
app.include_router(latest_news_routes.router)

@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.png", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/")
def root():
    return {"status": "ok", "message": "sammridhvarma API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
