import sqlite3
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from utils.tools import load_conf

config = load_conf()
site_config = config.get('site')
hardware = site_config.get('hardware')

tasks_cash = Path(hardware.get('tasks_cash_filepath'))
employees_cash = hardware.get('employees_cash_filepath')
backup_folder = hardware.get('backup_path')
log_path = hardware.get('log_filepath')
db_path = hardware.get('database_path')

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"
Base = declarative_base()


class MattressRequest(Base):
    __tablename__ = 'mattress_requests'

    id = Column(Integer, primary_key=True)
    high_priority = Column(Boolean, default=False)
    deadline = Column(Date)
    article = Column(String)
    size = Column(String)
    base_fabric = Column(String)
    side_fabric = Column(String)
    springs = Column(String, default='Нет')
    photo = Column(String, default='')
    components_is_done = Column(Boolean, default=False)
    fabric_is_done = Column(Boolean, default=False)
    gluing_is_done = Column(Boolean, default=False)
    sewing_is_done = Column(Boolean, default=False)
    packing_is_done = Column(Boolean, default=False)
    comment = Column(String, default='')
    history = Column(String, default='')
    attributes = Column(String)
    created = Column(Date)

    order_id = Column(Integer, ForeignKey('orders.id'))
    order = relationship("Order", back_populates="mattress_requests")


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    organization = Column(String)
    delivery_type = Column(String)
    contact = Column(String)
    address = Column(String)
    region = Column(String)
    created = Column(Date)

    # Отношение "один-ко-многим" к MattressRequest
    mattress_requests = relationship("MattressRequest", back_populates="order")


engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Database connection
def get_db_connection():
    conn = sqlite3.connect(db_path)
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
