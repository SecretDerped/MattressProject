from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    is_on_shift = Column(Boolean, default=False)
    name = Column(String)
    position = Column(String)
    barcode = Column(String)


class EmployeeTask(Base):
    __tablename__ = 'employee_tasks'

    id = Column(Integer, primary_key=True)
    employee_id: Column[int] = Column(Integer, ForeignKey('employees.id'))
    task_id: Column[int] = Column(Integer, ForeignKey('mattress_requests.id'))
    endpoint: Column[str] = Column(String)
    timestamp = Column(DateTime, default=datetime.now())

    employee = relationship('Employee')
    task = relationship('MattressRequest')


class MattressRequest(Base):
    __tablename__ = 'mattress_requests'

    id = Column(Integer, primary_key=True)
    high_priority = Column(Boolean, default=False)
    article = Column(String)
    size = Column(String)
    base_fabric = Column(String)
    side_fabric = Column(String)
    springs = Column(String, default='')
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
    deadline = Column(Date)
    created = Column(Date)

    # Отношение "один-ко-многим" к MattressRequest
    mattress_requests = relationship("MattressRequest", back_populates="order")