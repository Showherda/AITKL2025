from sqlalchemy.sql import select
from sqlalchemy import create_engine
import dotenv
import os
# from models import startups
from sqlalchemy import Column, Integer, String, Boolean, JSON, create_engine, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import dotenv
import os

meta = MetaData()

# Load environment variables from .env file
dotenv.load_dotenv()

DB_URL = os.getenv("AIVEN_CONNECTION_STRING")

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

def get_startups():
    engine = create_engine(DB_URL, echo=True)
    conn = engine.connect()
    s = select(startups)

    result = conn.execute(s)
    data = result.fetchall()

    # Convert the result into a json serializable format
    data_list = []
    for row in data:
        data_list.append({
            "id": row.id,
            "logo": row.logo,
            "name": row.name,
            "company_description": row.company_description,
            "summary": row.summary,
            "status": row.status,
            "website_url": row.website_url,
            "founding_year": row.founding_year,
            "startup_category": row.startup_category,
            "founding_team_size": row.founding_team_size,
            "magic_accredited": row.magic_accredited,
            "employees": row.employees,
            "location": row.location,
            "founder": row.founder
        })

    # Close the connection
    conn.close()

    return data_list
