from sqlmodel import SQLModel, create_engine

DATABASE_URL = "sqlite:///mca_crm.db"  # switch to Postgres if needed
engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    from models.merchant import Merchant  # import all models
    SQLModel.metadata.create_all(engine)
