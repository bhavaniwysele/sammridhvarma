from fastapi import FastAPI
from app.database import Base, engine
from app.routes.latest_news_routes import router as news_router
from fastapi.staticfiles import StaticFiles
app = FastAPI()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Create tables
Base.metadata.create_all(bind=engine)

# Register routes
app.include_router(news_router)


@app.get("/")
def root():
    return {"message": "Latest News API running 🚀"}