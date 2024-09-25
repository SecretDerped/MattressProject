from pathlib import Path
from psycopg2 import connect
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from utils.models import Base
from utils.tools import load_conf

config = load_conf()
site_config = config.get('site')
hardware = site_config.get('hardware')

tasks_cash = Path(hardware.get('tasks_cash_filepath'))
employees_cash = hardware.get('employees_cash_filepath')
backup_folder = hardware.get('backup_path')
log_path = hardware.get('log_filepath')
db_path = hardware.get('database_path')
db_name = "mattresses_requests"
db_user = "postgres"
db_password = "1111111111111111"
db_host = 'localhost'
db_port = 5432

# Create synchronous engine and session
DATABASE_URL_SYNC = f"postgresql://{db_user}:{db_password}@localhost/{db_name}"
engine = create_engine(DATABASE_URL_SYNC)
session = sessionmaker(bind=engine)

# Asynchronous Database URL
DATABASE_URL_ASYNC = f"postgresql+asyncpg://{db_user}:{db_password}@localhost/{db_name}"
async_engine = create_async_engine(DATABASE_URL_ASYNC, echo=True)
async_session = sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)


# Database connection
def get_db_connection():
    # Укажите параметры подключения
    conn = connect(
        user=db_user,
        password=db_password,
        database=db_name,
        host='localhost',
        port=db_port
    )
    return conn


# Read from database
def read_from_db(query):
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# Save to database
def save_to_db(dataframe, table_name):
    conn = get_db_connection()
    dataframe.to_sql(table_name, conn, if_exists='append', index=False)
    conn.close()


# Update or delete operations
def update_db(query):
    conn = get_db_connection()
    conn.execute(query)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Create tables
    Base.metadata.create_all(engine)
