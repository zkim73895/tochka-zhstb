import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Body, APIRouter
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from typing import List
from uuid import UUID, uuid4
import secrets
import hashlib
import hmac

#DB operations stored as functions
import database as db_fnc

# Pydantic models
from schemas import (
    User, UserCreate, Instrument, InstrumentCreate, UserRole,
    MarketOrder, MarketOrderCreate, LimitOrder, LimitOrderCreate,
    Ok, AlterBalanceRequest
)

#Config
app = FastAPI(title="Stock Exchange API", version="0.2.2")
db = db_fnc.main_cursor

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

    rec = db_fnc.get_user_by_api_key(hashed_key)
    if not rec:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not secure_compare(rec["api_key_hashed"], hashed_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return User(id=rec["user_id"], name=rec["name"], role=rec["role"], api_key = hashed_key if USE_HASHED_API_KEYS else raw_key)

# Role-checking dependency factory
def require_role(required_role: UserRole):
    async def _dependency(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return current_user
    return _dependency


# Basic routes
@app.get("/")
async def root():
    return {"message": "Stock Exchange API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

###

#Public endpoints, no API token required
@app.post("/api/v1/public/register", response_model=User)
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


#Admin endpoints, ADMIN user role dependency check included
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_role(UserRole.ADMIN))])

@admin_router.delete("/user/{user_id}", response_model=User)
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


@admin_router.post("/balance/deposit", response_model=Ok)
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


@admin_router.post("/balance/withdraw", response_model=Ok)
async def admin_withdraw(request: AlterBalanceRequest):
    return await update_balance(request, is_deposit=False)



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)