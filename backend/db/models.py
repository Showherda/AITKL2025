from sqlalchemy import Column, Integer, String, Boolean, JSON, create_engine, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import dotenv
import os

# Load environment variables from .env file
dotenv.load_dotenv()
DB_URL = os.getenv("AIVEN_CONNECTION_STRING")
engine = create_engine(DB_URL, echo=True)
meta = MetaData()

startups = Table(
    'startups', meta,
    Column('id', Integer, primary_key=True),
    Column('logo', String),
    Column('name', String, nullable=False),
    Column('company_description', String),
    Column('summary', String),
    Column('status', Boolean),  # True = active, False = inactive
    Column('website_url', String),
    Column('founding_year', String),
    Column('startup_category', String),
    Column('founding_team_size', String),
    Column('magic_accredited', Boolean),
    Column('employees', JSONB),  # List of dicts
    Column('location', String),
    Column('founder', JSONB)  # Dict with founder details
)
if __name__ == "__main__":
    # Create the table in the database
    meta.create_all(engine)