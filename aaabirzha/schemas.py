from typing import List

from pydantic import BaseModel, field_validator
from enum import Enum, IntEnum, StrEnum
from datetime import datetime
from uuid import UUID
from re import fullmatch


# Enums
class Direction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"

    @classmethod
    def from_int(cls, v):
        return cls("BUY" if v == 0 else "SELL")
    @classmethod
    def to_int(cls, v):
        return v == "SELL"


class OrderStatus(StrEnum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PART_EXECUTED = "PART_EXECUTED"
    CANCELLED = "CANCELLED"

    @classmethod
    def from_int(cls, v):
        val_list = ['NEW', 'EXECUTED', 'PART_EXECUTED', 'CANCELLED']
        return cls(val_list[v])
    @classmethod
    def to_int(cls, v):
        val_list = ['NEW', 'EXECUTED', 'PART_EXECUTED', 'CANCELLED']
        return val_list.index(v)


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"

    @classmethod
    def from_int(cls, v):
        return cls("ADMIN" if v == 1 else "USER")
    @classmethod
    def to_int(cls, v):
        return 0 if v == "USER" else 1


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

    # @field_validator('direction', mode="before")
    # def convert_direction(cls, value):
    #     return Direction.from_str(value)


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

    # @field_validator('direction', mode="before")
    # def convert_direction(cls, value):
    #     if isinstance(value, str):
    #         return Direction.from_str(value)
    #     else:
    #         return value

class LimitOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    body: LimitOrderBody
    timestamp: datetime
    filled: int = 0

    class Config:
        from_attributes = True


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

    @classmethod
    def from_int(cls, v):
        return cls("LIMIT" if v == 1 else "MARKET")
    @classmethod
    def to_int(cls, v):
        return 0 if v == "MARKET" else 1


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


class Level(BaseModel):
    price: float
    qty: float

class L2OrderBook(BaseModel):
    bid_levels: List[Level]
    ask_levels: List[Level]