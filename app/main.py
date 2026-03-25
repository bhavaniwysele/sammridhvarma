import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.routes.latest_news_routes import router as news_router
from app.routes.appointment_routes import router 
from app.models.appointments import Appointment  

app = FastAPI(title="sammridhvarma")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

Base.metadata.create_all(bind=engine)

app.include_router(news_router)
app.include_router(router)
