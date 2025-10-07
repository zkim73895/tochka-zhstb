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
    name: str
    ticker: str


# Order schemas
class MarketOrderBody(BaseModel):
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
    body: MarketOrderBody
    timestamp: datetime

    class Config:
        from_attributes = True


class LimitOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int
    price: int

    @field_validator('qty')
    @classmethod
    def check_qty(cls, value):
        if value < 1:
            raise ValueError('Order quantity may not be less than 1')
        return value

    @field_validator('price')
    @classmethod
    def check_price(cls, value):
        if value <= 0:
            raise ValueError('Price may not be 0 or negative')
        return value


class LimitOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    body: LimitOrderBody
    timestamp: datetime
    filled: int = 0

    class Config:
        from_attributes = True


class OrderType(IntEnum):
    MARKET = 0
    LIMIT = 1


class Transaction(BaseModel):
    ticker: str
    amount: int
    price: float
    timestamp: datetime


class Ok(BaseModel):
    success: bool = True


class AlterBalanceRequest(BaseModel):
    user_id: UUID
    ticker: str
    amount: int

    @field_validator('amount')
    @classmethod
    def is_non_negative(cls, amount: int) -> int:
        if amount < 0:
            raise ValueError('Amount may not be negative')
        return amount
