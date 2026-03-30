import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.database import Base, engine

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


@app.on_event("startup")
def startup():
    try:
        if engine:
            Base.metadata.create_all(bind=engine)
    except Exception as e:
        print("DB INIT ERROR:", e)


try:
    from app.routes import press_release_routes
    app.include_router(press_release_routes.router)
except Exception as e:
    print("press_release error:", e)

try:
    from app.routes import appointment_routes
    app.include_router(appointment_routes.router)
except Exception as e:
    print("appointment error:", e)

try:
    from app.routes import issue_routes
    app.include_router(issue_routes.router)
except Exception as e:
    print("issue error:", e)

try:
    from app.routes import latest_news_routes
    app.include_router(latest_news_routes.router)
except Exception as e:
    print("latest_news error:", e)


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
