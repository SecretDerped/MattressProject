from pathlib import Path
import psycopg2
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from utils.models import Base, MattressRequest, Order
from utils.tools import load_conf

config = load_conf()
site_config = config.get('site')
hardware = site_config.get('hardware')

tasks_cash = Path(hardware.get('tasks_cash_filepath'))
employees_cash = hardware.get('employees_cash_filepath')
backup_folder = hardware.get('backup_path')
log_path = hardware.get('log_filepath')
db_path = hardware.get('database_path')
db_name = "postgres"
db_user = "postgres"
db_password = "0-=0-="
db_port = "5432"
db_host = 'localhost'

# Create synchronous engine and session
DATABASE_URL_SYNC = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}"
engine = create_engine(DATABASE_URL_SYNC, echo=True)
session = sessionmaker(bind=engine)

# Asynchronous Database URL
DATABASE_URL_ASYNC = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}/{db_name}"
async_engine = create_async_engine(DATABASE_URL_ASYNC, echo=True)
async_session = sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)


# Database connection
# Укажите параметры подключениѝ
def get_db_connection():
    conn = psycopg2.connect(
        user=db_user,
        password=db_password,
        database=db_name,
        host=db_host,
        port=db_port,
    )
    return conn


# Read from database
def read_from_db(query):
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn, coerce_float=True)
    conn.close()
    return df


# Save to database
def save_to_db(dataframe, table_name):
    conn = get_db_connection()
    dataframe.to_sql(table_name, conn, if_exists='replace', index=True)
    conn.close()


def load_tasks(session):
    # Возвращает вѝе заказы в порѝдке id. Еѝли нужно ѝортировать в порѝдке убываниѝ, иѝпользуй Order.id.desc()
    return session.query(MattressRequest).order_by(Order.id.desc()).limit(100).all()


if __name__ == "__main__":
    Base.metadata.create_all(engine)
