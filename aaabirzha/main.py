import random

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Body
from typing import List
from uuid import UUID, uuid4

import database as db_fnc

# Import all modules
from schemas import (
    User, UserCreate, Instrument, InstrumentCreate,
    MarketOrder, MarketOrderCreate, LimitOrder, LimitOrderCreate,
    OrderMessage
)


app = FastAPI(title="Stock Exchange API", version="1.0.0")
db = db_fnc.cursor



# Basic routes
@app.get("/")
async def root():
    return {"message": "Stock Exchange API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

###

@app.post("/api/v1/public/register", response_model=User)
async def create_user(data: UserCreate):
    try:
        user = User(
            id=uuid4(),
            name=data.name,
            api_key='N/A'
        )
        db_fnc.create_user(user.id, user.name, user.role, user.api_key)
        return user
    except Exception:
        raise HTTPException(status_code=422, detail="Validation Error")

# @app.get("/api/v1/public/instrument")
# async def get_instruments():
#     pass
#
#
#
#
# ###
#
#
# # User routes
# @app.post("/users", response_model=User)
# def create_user(user: UserCreate):
#     # Check if API key already exists
#     existing_user = None
#     if existing_user:
#         raise HTTPException(status_code=400, detail="API key already exists")
#
# @app.get("/users/{user_id}", response_model=User)
# def get_user(user_id: str):
#     pass
#
#
# # Instrument routes
# @app.post("/instruments", response_model=Instrument)
# def create_instrument(instrument: InstrumentCreate):
#     pass
#
# @app.get("/instruments", response_model=List[Instrument])
# def list_instruments():
#     instruments = None
#     return [
#         Instrument(id=inst.id, name=inst.name, ticker=inst.ticker)
#         for inst in instruments
#     ]
#
#
# @app.get("/instruments/{ticker}", response_model=Instrument)
# def get_instrument(ticker: str):
#     pass
#
# # Order routes
# @app.post("/orders/market", response_model=MarketOrder)
# async def create_market_order(
#         order: MarketOrderCreate,
#         api_key: str
# ):
#     pass
#
#
#
# @app.post("/orders/limit", response_model=LimitOrder)
# async def create_limit_order(
#         order: LimitOrderCreate,
#         api_key: str
# ):
#     pass
#
#
# @app.get("/orders/market/{order_id}", response_model=MarketOrder)
# def get_market_order(order_id: str):
#     pass
#
#
# @app.get("/orders/limit/{order_id}", response_model=LimitOrder)
# def get_limit_order(order_id: str):
#     pass
#
# # Get user's orders
# @app.get("/users/{user_id}/orders/market", response_model=List[MarketOrder])
# def get_user_market_orders(user_id: str):
#     pass
#
#
# @app.get("/users/{user_id}/orders/limit", response_model=List[LimitOrder])
# def get_user_limit_orders(user_id: str):
#     pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)