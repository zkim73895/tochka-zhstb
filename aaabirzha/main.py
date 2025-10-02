import random

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import List
from uuid import UUID, uuid4

import database as db_fnc

# Import all modules
from schemas import (
    User, UserCreate, Instrument, InstrumentCreate,
    MarketOrder, MarketOrderCreate, LimitOrder, LimitOrderCreate,
    Ok, AlterBalanceRequest
)


app = FastAPI(title="Stock Exchange API", version="1.0.0")
db = db_fnc.main_cursor



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
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")

@app.delete("/api/v1/admin/user/{user_id}", response_model=User)
async def delete_user(user_id: UUID):
    try:
        user_data = db_fnc.delete_user(user_id)
        user = User(
            id=user_data['user_id'],
            name=user_data['name'],
            role=user_data['role'],
            api_key=user_data['api_key']
        )
        return user
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")


@app.post("/api/v1/admin/instrument", response_model=Ok)
async def create_instrument(create_request: InstrumentCreate):
    try:
        instrument = Instrument(
            name = create_request.name,
            ticker = create_request.ticker
        )
        db_fnc.create_instrument(instrument.name, instrument.ticker)
        return Ok()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")


@app.post("/api/v1/admin/balance/deposit", response_model=Ok)
async def update_balance(request: AlterBalanceRequest, is_deposit=True):
    if not db_fnc.lookup('Users', 'id', str(request.user_id)):
        raise HTTPException(status_code=422, detail='User not found')
    try:
        db_fnc.update_balance(request.user_id, request.ticker, request.amount, is_deposit)
        return Ok()
    except Exception as e:
        if isinstance(e, ValueError):
            raise HTTPException(status_code=422, detail=f'Unprocessable content: {e}')
        else:
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@app.post("/api/v1/admin/balance/withdraw", response_model=Ok)
async def admin_withdraw(request: AlterBalanceRequest):
    return await update_balance(request, is_deposit=False)


# @app.get("/api/v1/balance")
# async def get_balance():
#     pass


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