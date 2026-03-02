"""One-time script to create the marketmonitor database."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

url = os.environ["DATABASE_URL"]
# Connect to the default 'postgres' database to issue CREATE DATABASE
admin_url = url.rsplit("/", 1)[0] + "/postgres"

conn = psycopg2.connect(admin_url)
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'marketmonitor'")
if cur.fetchone():
    print("Database 'marketmonitor' already exists.")
else:
    cur.execute("CREATE DATABASE marketmonitor")
    print("Database 'marketmonitor' created successfully.")
conn.close()
