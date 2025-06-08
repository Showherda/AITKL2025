import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from models import startups
import dotenv
import os

# Load environment variables from .env file
dotenv.load_dotenv()

DB_URL = os.getenv("AIVEN_CONNECTION_STRING")
engine = create_engine(DB_URL, echo=True)
con = engine.connect()

# Load data from a Gemini-extracted JSON
with open("../scraper/structured_output.json", "r", encoding="utf-8") as f:
    data = f.readlines()

for datum in data:
    data = json.loads(datum)

    stmt = startups.insert().values(
        logo=data.get("logo"),
        name=data["name"],
        company_description=data.get("company_description"),
        summary=data.get("summary"),
        status=(data.get("status") == "active" or data.get("status") == "1"),
        website_url=data.get("website_url"),
        founding_year=data.get("founding_year"),
        startup_category=data.get("startup_category"),
        founding_team_size=data.get("founding_team_size"),
        magic_accredited=data.get("magic_accredited") in [True, "true", "True", "1"],
        employees=data.get("employees"),
        location=data.get("location"),
        founder=data.get("founder")
    )
    result = con.execute(stmt)

print("✅ Startup inserted into DB.")
