from sqlalchemy.sql import select
from sqlalchemy import create_engine
import dotenv
import os
from models import startups

# Load environment variables from .env file
dotenv.load_dotenv()

DB_URL = os.getenv("AIVEN_CONNECTION_STRING")
engine = create_engine(DB_URL, echo=True)
conn = engine.connect()

s = select(startups)

result = conn.execute(s)
data = result.fetchall()
print(data)
