import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def build_database_url():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")

    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


DATABASE_URL = build_database_url()

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()