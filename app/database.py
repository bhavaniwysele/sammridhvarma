import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

Base = declarative_base()

engine = None
SessionLocal = None

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, poolclass=NullPool)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    if not SessionLocal:
        raise RuntimeError("DATABASE_URL is not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
