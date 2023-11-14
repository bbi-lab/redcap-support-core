import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# TODO Move these to a central config object.
DB_HOST = os.getenv("DB_HOST") or "localhost"
DB_PORT = os.getenv("DB_PORT") or 5432
DB_DATABASE_NAME = os.getenv("DB_DATABASE_NAME")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DB_URL = (
    f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE_NAME}"
)

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
