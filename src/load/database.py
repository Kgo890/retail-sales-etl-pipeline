from sqlalchemy import create_engine
import os
from dotenv import load_dotenv


load_dotenv()

db_url = os.getenv("DATABASE_URL")

print("DATABASE_URL loaded:", db_url is not None)

engine = create_engine(db_url)

try:
    with engine.connect() as connection:
        print("Successfully connected to PostgreSQL!")
except Exception as e:
    print(f"Database connection failed: {e}")