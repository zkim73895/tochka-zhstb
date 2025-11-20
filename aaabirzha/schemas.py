from pydantic import BaseModel, field_validator
from enum import Enum, IntEnum
from datetime import datetime
from uuid import UUID
from typing import Optional
from re import fullmatch


# Enums
class Direction(IntEnum):
    BUY = 0
    SELL = 1

    @classmethod
    def from_str(cls, string):
        return cls(0 if string == 'BUY' else 1)


class OrderStatus(IntEnum):
    NEW = 0
    EXECUTED = 1
    PART_EXECUTED = 2
    CANCELLED = 3

    @classmethod
    def from_str(cls, string):
        val_list = ['NEW', 'EXECUTED', 'PART_EXECUTED', 'CANCELLED']
        return val_list.index(string)


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

    model_config = {"union_mode": "smart"}

    @field_validator('qty')
    def check_qty(cls, value):
        if value < 1:
            raise ValueError('Order quantity may not be less than 1')
        return value

    @field_validator('direction', mode="before")
    def convert_direction(cls, value):
        return Direction.from_str(value)


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

    model_config = {"union_mode": "smart"}

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

    @field_validator('direction', mode="before")
    def convert_direction(cls, value):
        if isinstance(value, str):
            return Direction.from_str(value)
        else:
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


class TransactionBody(BaseModel):
    ticker: str
    qty: int
    price: float
    timestamp: datetime


class Transaction(BaseModel):
    user_id: UUID
    init_order: UUID
    target_order: UUID
    direction: Direction
    body: TransactionBody


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
