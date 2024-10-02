import threading
from pathlib import Path

import psycopg2
from psycopg2 import connect
import pandas as pd
from sqlalchemy import create_engine, event
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


def listen_for_notifications():
    conn = get_db_connection()
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute("LISTEN mattress_changes;")

    while True:
        conn.poll()  # Check for notifications
        while conn.notifies:
            notify = conn.notifies.pop(0)
            print(f"Received notification: {notify.payload}")
            # Here you can set a flag or call a function to refresh the data in your Streamlit app


# Save to database
def save_to_db(dataframe, table_name):
    conn = get_db_connection()
    dataframe.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()


# Update or delete operations
def update_db(query):
    conn = get_db_connection()
    conn.execute(query)
    conn.commit()
    conn.close()


def load_tasks(session):
    # Возвращает все заказы в порядке id. Если нужно сортировать в порядке убывания, используй Order.id.desc()
    return session.query(MattressRequest).order_by(Order.id.desc()).limit(100).all()


# Assuming you're using SQLAlchemy for your database operations
def notify_changes(mapper, connection, target):
    connection.execute("NOTIFY mattress_changes")


# Register the listener for insert, update, and delete events
event.listen(MattressRequest, 'after_insert', notify_changes)
event.listen(MattressRequest, 'after_update', notify_changes)
event.listen(MattressRequest, 'after_delete', notify_changes)

listener_thread = threading.Thread(target=listen_for_notifications, daemon=True)
listener_thread.start()

if __name__ == "__main__":
    # Create tables
    Base.metadata.create_all(engine)
