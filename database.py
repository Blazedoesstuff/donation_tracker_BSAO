
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# Stores the database in a local file.
DATABASE_URL = "sqlite:///bsao.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


# Base class for all database models.
class Base(DeclarativeBase):
    pass


# Creates database sessions for reading and writing data.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)


def get_session():
    """Create a database session."""
    return SessionLocal()
