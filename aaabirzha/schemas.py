from pydantic import BaseModel, field_validator
from enum import Enum, IntEnum
from datetime import datetime
from uuid import UUID
from typing import Optional
from re import fullmatch


# Enums
class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PART_EXECUTED = "PART_EXECUTED"
    CANCELLED = "CANCELLED"


class UserRole(IntEnum):
    USER = 0
    ADMIN = 1


# User schemas
class UserCreate(BaseModel):
    name: str


class User(BaseModel):
    id: UUID
    name: str
    role: UserRole = UserRole.USER
    api_key: str


# Instrument schemas
class InstrumentCreate(BaseModel):
    name: str
    ticker: str

    @field_validator('ticker')
    def check_ticker(cls, value):
        if not fullmatch(r'^[A-Z]{2,10}$', value):
            raise ValueError(f'Invalid ticker "{value}"')
        return value


class Instrument(BaseModel):
    id: Optional[int] = None
    name: str
    ticker: str

    class Config:
        from_attributes = True


# Order schemas
class MarketOrderCreate(BaseModel):
    direction: Direction
    ticker: str
    qty: int

    @field_validator('qty')
    def check_qty(cls, value):
        if value < 1:
            raise ValueError('Order quantity may not be less than 1')
        return value


class MarketOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    direction: Direction
    ticker: str
    qty: int
    timestamp: datetime

    class Config:
        from_attributes = True


class LimitOrderCreate(BaseModel):
    direction: Direction
    ticker: str
    qty: int
    price: int

    @field_validator('qty')
    def check_qty(cls, value):
        if value < 1:
            raise ValueError('Order quantity may not be less than 1')
        return value

    @field_validator('price')
    def check_price(cls, value):
        if value <= 0:
            raise ValueError('Price may not be 0 or negative')
        return value


class LimitOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    direction: Direction
    ticker: str
    qty: int
    price: int
    timestamp: datetime

    class Config:
        from_attributes = True


# Message schemas for RabbitMQ
class OrderMessage(BaseModel):
    order_id: str
    order_type: str  # "market" or "limit"
    user_id: str
    ticker: str
    direction: Direction
    qty: int
    price: Optional[int] = None
    timestamp: datetime