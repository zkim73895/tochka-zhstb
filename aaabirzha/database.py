import sqlite3 as sql
from schemas import MarketOrder, LimitOrder
conn = sql.connect('database.db')

conn.execute('PRAGMA journal_mode=WAL;')

main_cursor = conn.cursor()

def create_user(id, name, role, api_key_hashed, api_key=None):
    cursor = conn.cursor()
    query = f'''
    INSERT INTO Users (id, name, role, api_key_hashed, api_key)
    VALUES (?, ?, ?, ?, ?);
    '''
    try:
        cursor.execute(query, (str(id), name, int(role), api_key_hashed, api_key))
    except Exception as e:
        print(e)
    print(f'User {name} created successfully')
    conn.commit()
    cursor.close()


def create_instrument(name, ticker):
    cursor = conn.cursor()
    print(f'name: {name}, ticker: {ticker}')
    query = '''
    INSERT INTO Instruments (name, ticker)
    VALUES (?, ?);
    '''
    try:
        cursor.execute(query, (name, ticker,))
        print(f'Instrument {name}:{ticker} created successfully')
        conn.commit()
    except Exception as e:
        print('Failed to create instrument')
        print(e)
    cursor.close()


def delete_instrument(ticker):
    cursor = conn.cursor()
    print(f'Trying to delete instrument with ticker "{ticker}"')
    query = '''
    DELETE FROM Instruments
    WHERE ticker = ?'''
    try:
        cursor.execute(query, (ticker))
        print(f'Instrument {ticker} deleted')
        conn.commit()
    except sql.DatabaseError as e:
        print(f'DBError: Failed to delete instrument {ticker}\n{e}')
    cursor.close()


def new_ticker(user_id, ticker):
    cursor = conn.cursor()
    query = '''
    INSERT INTO UserBalance (user_id, ticker)
    VALUES (?, ?)
    '''

    print(f'Trying to add {ticker} balance for user {user_id} ')

    try:
        cursor.execute(query, (user_id, ticker))
        print(f'{ticker} balance added to user {user_id}')
        conn.commit()
    except sql.DatabaseError as e:
        print(f'DBError: Failed to add ticker {ticker} to user {user_id}\n{e}')
    cursor.close()


def update_balance(user_id, ticker, amount: int, is_deposit: bool):
    cursor = conn.cursor()
    user_id = str(user_id)

    print(f'''user_id:{user_id}
ticker: {ticker}
amount: {amount}
type: {'deposit' if is_deposit else 'withdraw'}''')

    balance = lookup_balance(user_id, ticker)

    print(f'Balance: {balance}')

    if not balance:
        print(f'User {user_id} does not have a {ticker} balance')
        if is_deposit:
            new_ticker(user_id, ticker)
            print(f'{ticker} balance created')
    if not is_deposit:
        if amount > balance:
            return ValueError("Cannot withdraw more than the current balance")
        amount = 0 - amount
    query = '''
    UPDATE UserBalance 
    SET balance = balance + ?
    WHERE user_id = ? AND ticker = ?
    '''
    try:
        cursor.execute(query, (amount, user_id, ticker))
        print(f'''Transaction made. Type is deposit: {is_deposit}
        User: {user_id}
        Ticker {ticker} balance updated from {balance} to {balance + amount}''')
        conn.commit()
    except sql.DatabaseError as e:
        print(f'Failed to add ticker {ticker} to user {user_id}\n{e}')
    cursor.close()


def lookup(table, key, val):
    cursor = conn.cursor()
    query = f'''
    SELECT * FROM {table} WHERE {key} = ?
    '''
    cursor.execute(query, (val,))
    result = cursor.fetchone()
    cursor.close()
    return result


def lookup_balance(user_id, ticker=None):
    cursor = conn.cursor()

    #If no ticker is specified, returns all tickers for the user
    if not ticker:
        query = f'''
SELECT ticker, balance FROM UserBalance
WHERE user_id = ?'''
        print(f'Trying to look up balance of all instruments for user {user_id}')

        cursor.execute(query, (user_id,))
        response = cursor.fetchall()
        return response

    query = f'''
    SELECT balance FROM UserBalance 
    WHERE user_id = ? AND ticker = ?
    '''

    print(f'Trying to look up {ticker} balance for {user_id}\nQuery:\n{query}')

    cursor.execute(query, (user_id, ticker))
    response = cursor.fetchone()

    print(f'Response: {response}')

    cursor.close()
    return response

def delete_user(user_id):
    cursor = conn.cursor()

    query = f'''
SELECT * FROM Users
WHERE user_id = ?'''

    query1 = f'''
DELETE FROM Users
WHERE user_id = ?'''

    try:
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        if not user:
            print('User not found')
            raise Exception(f"Cannot delete a non-existent user:\nUser {user_id} not found in the database")

        print(f'Trying to delete user {user_id}\nQuery:\n{query1}')
        cursor.execute(query1, (user_id,))
    except sql.DatabaseError as e:
        print(f'DBError: Failed to delete user {user_id}\n{e}')

    cursor.close()
    return user

def get_user_by_api_key(api_key, hashed=True):
    api_key_column = 'api_key_hashed' if hashed else 'api_key'
    cursor = conn.cursor()
    query = f'''
SELECT id, name, role, {api_key_column}
FROM Users
WHERE {api_key_column} = ?'''
    try:
        cursor.execute(query, (api_key,))
        user = cursor.fetchone()
        if not user:
            print('User not found')
            raise Exception(f"User not found")
    except sql.DatabaseError as e:
        print(f'DBError: Failed to get user by api_key = {api_key}\n{e}')


def create_market_order(order = MarketOrder):
    cursor = conn.cursor()
    query = f'''
INSERT INTO MarketOrders
(id, status, user_id, timestamp, direction, ticker, qty)
VALUES (?, ?, ?, ?, ?, ?, ?)'''
    try:
        cursor.execute(query, (order.id, order.status, order.timestamp, order.direction, order.ticker, order.qty))
    except sql.DatabaseError as e:
        print(f'DBError: Failed to create order: {order.model_dump()}\n{e}')

def temp():
    try:
        pass
    except sql.DatabaseError as e:
        print(f'DBError: Failed to AAAAAA\n{e}')

# print(
#     'sanya loh'
# )
