import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Body, APIRouter
from fastapi.security import APIKeyHeader
from typing import Optional, Union, List
from uuid import UUID, uuid4
from datetime import datetime
import secrets
import hashlib
import hmac
import logging

#DB operations stored as functions
import database as db_fnc
from aaabirzha.database import quotify_ticker
from aaabirzha.matching_engine import execute_market_order, execute_limit_order
from aaabirzha.schemas import OrderStatus, Direction

# Pydantic models
from schemas import (
    User, UserCreate, Instrument, InstrumentCreate, UserRole,
    MarketOrder, MarketOrderBody, LimitOrder, LimitOrderBody,
    Ok, AlterBalanceRequest, Transaction
)

#Config
app = FastAPI(title="Stock Exchange API", version="0.3.1")
db = db_fnc.main_cursor

logging.basicConfig(
    level=logging.DEBUG,       # show debug and above
    format="[%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

#A toggle to (dis)allow the use of unhashed api keys
#Users created while the toggle is ON will have no unhashed api_key, beware of unexpected behaviour
#Схема на swagger не подразумевает хэширование ключей, но вообще учитывая контекст биржи и финансовых операций,
#такой функционал бы пригодился
USE_HASHED_API_KEYS = False

auth_header = APIKeyHeader(name="Authorization", auto_error=False)

def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

def secure_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)

def parse_token_header(header: str) -> str:
    if not header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    try:
        scheme, token = header.split(" ", 1)
    except ValueError:
        raise HTTPException(status_code=401, detail="Malformed Authorization header")
    if scheme != "TOKEN":
        raise HTTPException(status_code=401, detail="Invalid auth scheme (use 'TOKEN')")
    return token

#Get the user whose api key corresponds to the one in the header. Uses SHA256 regardless of the toggle
async def get_current_user(header_value: Optional[str] = Depends(auth_header)) -> User:
    raw_key = parse_token_header(header_value)
    hashed_key = hash_api_key(raw_key)
    logger.debug(raw_key + '\n' + hashed_key)

    rec = db_fnc.get_user_by_api_key(hashed_key)
    logger.debug(rec)
    if not rec:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not secure_compare(rec["api_key"], hashed_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return User(id=rec["id"], name=rec["name"], role=rec["role"], api_key = hashed_key if USE_HASHED_API_KEYS else raw_key)

# Role-checking dependency factory
def require_role(required_role: UserRole):
    async def _dependency(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return current_user
    return _dependency

#Makes sure a string is surrounded by double quotes: (RUB') -> "RUB"
#Intended to simplify parsing of quoteless query params like .../instrument/RUB instead of .../"RUB"
def quotify_param(param: str) -> str:
    param = param.replace('"', '').replace("'", '')
    return f'"{param}"'

# Basic routes
@app.get("/")
async def root():
    return {"message": "Stock Exchange API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

###

#Public endpoints, no API token required
public_router = APIRouter(prefix="/api/v1/public", tags=["public"])

@public_router.post("/register", response_model=User)
async def create_user(data: UserCreate):
    try:
        raw_key = f"key-{secrets.token_hex(16)}"
        hashed_key = hash_api_key(raw_key)
        user = User(
            id=uuid4(),
            name=data.name,
            api_key=hashed_key if USE_HASHED_API_KEYS else raw_key
        )
        db_fnc.create_user(user.id, user.name, user.role, hashed_key, None if USE_HASHED_API_KEYS else raw_key)
        return user
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")


@public_router.get("/instrument", response_model=List[Instrument])
async def get_instruments():
    try:
        instruments = [Instrument(
            name = instrument['name'],
            ticker = instrument['ticker']
            )
            for instrument in db_fnc.get_all_instruments()
        ]
        return instruments
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")


@public_router.get("/orderbook/{ticker}", response_model=List[Union[MarketOrder, LimitOrder]])
async def get_orderbook(ticker: str, limit: int = 10, current_user: User = Depends(get_current_user)):
    try:
        orderbook = [MarketOrder(order) if 'price' in order.keys() else LimitOrder(order)
                     for order in db_fnc.get_orders_for_user(current_user.id, ticker=quotify_param(ticker))]
        limit = min(limit, len(orderbook))
        return orderbook[:limit]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")


@public_router.get("/transactions/{ticker}")
async def get_transactions(ticker: str, limit: int = 10, current_user: User = Depends(get_current_user)):
    try:
        transactions = db_fnc.get_transactions_by_user(current_user.id, ticker=quotify_param(ticker))
        transactions = [Transaction(
            ticker = trans['ticker'],
            amount = trans['amount'],
            price = trans['price'],
            timestamp = trans['timestamp']
        )
            for trans in transactions
        ]
        limit = min(limit, len(transactions))
        return transactions[:limit]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")


@app.get("/api/v1/balance", tags=["balance"])
async def get_balance(current_user: User = Depends(get_current_user)):
    try:
        return db_fnc.lookup_balance(current_user.id, ticker=None)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")

app.include_router(public_router)


#Order endpoints
order_router = APIRouter(prefix="/api/v1/order", tags=["order"], dependencies=[Depends(get_current_user)])


@order_router.get('/')
async def get_orders(current_user: User = Depends(get_current_user)):
    try:
        return db_fnc.get_orders_for_user(str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")

@order_router.post('/')
async def create_order(create_request: Union[LimitOrderBody, MarketOrderBody], current_user: User = Depends(get_current_user)):
    try:
        if isinstance(create_request, MarketOrderBody):
            order = MarketOrder(
                id=uuid4(),
                status=OrderStatus.NEW,
                user_id=current_user.id,
                body = {
                    'direction': create_request.direction,
                    'ticker': create_request.ticker,
                    'qty': create_request.qty
                },
                timestamp=datetime.now()
            )
            await execute_market_order(order, current_user)
        else:
            order = LimitOrder(
                id=uuid4(),
                status=OrderStatus.NEW,
                user_id=current_user.id,
                body={
                    'direction': create_request.direction,
                    'ticker': create_request.ticker,
                    'qty': create_request.qty,
                    'price': create_request.price
                },
                timestamp=datetime.now()
            )
            db_fnc.create_limit_order(order, str(current_user.id))
            await execute_limit_order(order, current_user)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    return {"success": True, "order_id": order.id}

@order_router.get('/{order_id}', response_model=Union[MarketOrder, LimitOrder])
async def get_order_details(order_id: str):
    try:
        return db_fnc.get_order_by_id(quotify_param(order_id))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")

@order_router.delete('/{order_id}', response_model=Ok)
async def calcel_order(order_id: str):
    try:
        db_fnc.cancel_order(quotify_param(order_id))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")

app.include_router(order_router)


#Admin endpoints, ADMIN user role dependency check included
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_role(UserRole.ADMIN))])
# admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@admin_router.delete("/user/{user_id}", response_model=User, tags=["admin", "user"])
async def delete_user(user_id: UUID):
    try:
        user_data = db_fnc.delete_user(quotify_param(str(user_id)))
        user = User(
            id=user_data['user_id'],
            name=user_data['name'],
            role=user_data['role'],
            api_key=user_data['api_key']
        )
        return user
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")


@admin_router.post("/instrument", response_model=Ok)
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

@admin_router.delete("/instrument/{ticker}", response_model=Ok)
async def delete_instrument(ticker: str):
    try:
        db_fnc.delete_instrument(ticker)
        return Ok()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")


@admin_router.post("/balance/deposit", response_model=Ok, tags=["admin", "balance"])
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


@admin_router.post("/balance/withdraw", response_model=Ok, tags=["admin", "balance"])
async def admin_withdraw(request: AlterBalanceRequest):
    return await update_balance(request, is_deposit=False)

app.include_router(admin_router)



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)