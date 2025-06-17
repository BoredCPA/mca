# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database URL - using SQLite for development
SQLALCHEMY_DATABASE_URL = "sqlite:///./mca_crm.db"

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Only needed for SQLite
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


# Dependency function to get database session
def get_db() -> Session:
    """
    Database dependency function.
    Creates a new database session for each request and closes it when done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database function
def init_db():
    """
    Initialize the database by creating all tables.
    """
    # Import all models here to ensure they are registered with Base
    from app.models import merchant, offer

    # Create all tables
    Base.metadata.create_all(bind=engine)