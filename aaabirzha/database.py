import sqlite3 as sql
import logging
from gc import unfreeze

from aaabirzha.schemas import Direction
from schemas import MarketOrder, LimitOrder, OrderType, OrderStatus
from typing import Union


conn = sql.connect('database.db')

conn.execute('PRAGMA journal_mode=WAL;')

with open('Fresh_create_DB.sql', 'r') as freshstart_sql:
    freshstart_script = freshstart_sql.read()

main_cursor = conn.cursor()

main_cursor.executescript(freshstart_script)

logger = logging.getLogger(__name__)


def create_user(id, name, role, api_key_hashed, api_key=None):
    cursor = conn.cursor()
    users_query = f'''
    INSERT INTO Users (id, name, role, api_key_hashed, api_key)
    VALUES (?, ?, ?, ?, ?);
    '''
    userbalance_query = f'''
INSERT INTO UserBalance (user_id, ticker)
VALUES (?, 'RUB')'''
    try:
        cursor.execute(users_query, (str(id), name, int(role), api_key_hashed, api_key))
        cursor.execute(userbalance_query, (str(id),))
    except Exception as e:
        logger.error(e)
    logger.info(f'User {name} created successfully')
    conn.commit()
    cursor.close()


def create_instrument(name, ticker):
    cursor = conn.cursor()
    logger.debug(f'name: {name}, ticker: {ticker}')
    query = '''
    INSERT INTO Instruments (name, ticker)
    VALUES (?, ?);
    '''
    try:
        cursor.execute(query, (name, ticker,))
        logger.info(f'Instrument {name}:{ticker} created successfully')
        conn.commit()
    except Exception as e:
        logger.error(f'Failed to create instrument\n{e}')
    cursor.close()


def delete_instrument(ticker):
    cursor = conn.cursor()
    logger.info(f'Trying to delete instrument with ticker "{ticker}"')
    query = '''
    DELETE FROM Instruments
    WHERE ticker = ?'''
    logger.debug(f'Delete query:{query}')
    try:
        cursor.execute(query, (ticker,))
        logger.info(f'Instrument {ticker} deleted')
        conn.commit()
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to delete instrument {ticker}\n{e}')
    cursor.close()


def get_all_instruments():
    cursor = conn.cursor()
    query = '''
    SELECT DISTINCT name, ticker
    FROM Instruments'''
    try:
        cursor.execute(query)
        response = [jsonify(['name', 'ticker'], row) for row in cursor.fetchall()]
        cursor.close()
        return response
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to get all instruments\n{e}')


def new_ticker(user_id, ticker):
    cursor = conn.cursor()
    query = '''
    INSERT INTO UserBalance (user_id, ticker)
    VALUES (?, ?)
    '''

    logger.info(f'Trying to add {ticker} balance for user {user_id} ')

    try:
        cursor.execute(query, (user_id, ticker))
        logger.info(f'{ticker} balance added to user {user_id}')
        conn.commit()
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to add ticker {ticker} to user {user_id}\n{e}')
    cursor.close()


def update_balance(user_id, ticker, amount: float, is_freeze=False):
    cursor = conn.cursor()
    user_id = str(user_id)

    logger.debug(f'''user_id:{user_id}
ticker: {ticker}
amount: {amount}
type: {'deposit' if amount >= 0 else 'withdraw'}
is freeze: {is_freeze}''')

    balance = lookup_balance(user_id, ticker)['balance']

    logger.debug(f'Balance: {balance}')

    if not balance:
        logger.info(f'User {user_id} does not have a {ticker} balance')
        if amount >= 0:
            new_ticker(user_id, ticker)
            logger.info(f'{ticker} balance created')
    if amount < 0:
        if balance + amount < 0:
            raise ValueError(f"Cannot {"freeze" if is_freeze else "withdraw"} more than the current balance")

    column = "frozen" if is_freeze else "balance"
    query = f'''
    UPDATE UserBalance 
    SET {column} = {column} + ?
    WHERE user_id = ? AND ticker = ?
    '''
    try:
        cursor.execute(query, (amount, user_id, ticker))
        logger.info(f'''Transaction made. Type is deposit: {amount >= 0}
        User: {user_id}
        {f'Ticker {ticker} balance updated from {balance} to {balance + amount}'
        if not is_freeze else
        f'Ticker {ticker} frozen value changed by {amount}'}''')
        conn.commit()
    except sql.DatabaseError as e:
        logger.error(f'Failed to add ticker {ticker} to user {user_id}\n{e}')
    cursor.close()


def exchange_balance(buyer_id, seller_id, ticker, price: float, amount: float):
    try:
        # conn.execute('BEGIN TRANSACTION')
        update_balance(buyer_id, ticker, amount, False)
        update_balance(seller_id, 'RUB', amount * price, False)
        update_balance(seller_id, ticker, -amount, False)
        update_balance(buyer_id, 'RUB', -amount * price, False)
        # conn.execute('COMMIT')

    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to exchange balances\n{e}')
        # conn.execute('ROLLBACK')


def lookup(table, key, val):
    cursor = conn.cursor()
    query = f'''
    SELECT * FROM {table} WHERE {key} = ?
    '''
    logger.debug(f'db_fnc.lookup query:{query}')
    data = cursor.execute(query, (val,))
    columns = data.description
    result = jsonify([column[0] for column in columns], cursor.fetchone())
    logger.debug(f'db_fnc.lookup result:{result}')
    cursor.close()
    return result


def lookup_balance(user_id, ticker=None, available_only=False) -> dict:
    cursor = conn.cursor()

    #If no ticker is specified, returns all tickers for the user
    if not ticker:
        query = f'''
SELECT ticker, balance{'- frozen' if available_only else ''} 
FROM UserBalance
WHERE user_id = ?'''
        logger.info(f'Trying to look up balance of all instruments for user {user_id}')

        cursor.execute(query, (user_id,))
        response = [jsonify(['ticker', 'balance'], row) for row in cursor.fetchall()]
        cursor.close()
        return response

    query = f'''
    SELECT balance FROM UserBalance 
    WHERE user_id = ? AND ticker = ?
    '''

    logger.info(f'Trying to look up {ticker} balance for {user_id}\nQuery:\n{query}')

    cursor.execute(query, (user_id, ticker))
    response = jsonify(['balance'], cursor.fetchone())

    logger.debug(f'Response: {response}')

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
            logger.error('User not found')
            raise Exception(f"Cannot delete a non-existent user:\nUser {user_id} not found in the database")

        logger.info(f'Trying to delete user {user_id}\nQuery:\n{query1}')
        cursor.execute(query1, (user_id,))
        conn.commit()
        cursor.close()
        return user
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to delete user {user_id}\n{e}')
        cursor.close()
        raise e


def get_user_by_api_key(api_key, hashed=True):
    api_key_column = 'api_key_hashed' if hashed else 'api_key'
    cursor = conn.cursor()
    query = f'''
SELECT id, name, role, {api_key_column}
FROM Users
WHERE {api_key_column} = ?'''
    logger.debug(query)
    logger.debug(api_key)
    logger.debug(cursor.execute("SELECT * FROM Users").fetchall())
    try:
        cursor.execute(query, (api_key,))
        user = cursor.fetchone()
        if not user:
            logger.error(f'User with api key "{api_key}" not found')
            raise Exception(f"User not found")
        else:
            user = jsonify(['id', 'name', 'role', 'api_key'], user)
        return user
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to get user by api_key = {api_key}\n{e}')
        cursor.close()
        raise e


def trim_order(order, keep_type=False):
    if OrderType(order['type']) == OrderType.MARKET:
        order.pop('price', None)
        order.pop('filled', None)
    if not keep_type:
        order.pop('type', None)

    return order

order_fields = ['id', 'status', 'user_id', 'timestamp', 'direction',
                        'ticker', 'qty', 'price', 'filled', 'type']


def quotify_ticker(ticker: str):
    ticker = ticker.replace('"', '').replace("'", '')
    return f'"{ticker}"'


def get_orders_for_user(user_id, ticker=None):
    cursor = conn.cursor()
    if ticker:
        ticker = quotify_ticker(ticker)
    query = f'''
SELECT * FROM Orders
WHERE user_id = ?{f' AND ticker = {ticker}' if ticker else ''}'''
    logger.debug(f'Trying to get orders for user {user_id}. Query:{query}')
    try:
        cursor.execute(query, (str(user_id),))
        response = [trim_order(jsonify(order_fields, order)) for order in cursor.fetchall()]
        cursor.close()
        return response
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to get order list for user {user_id}\n{e}')
        cursor.close()
        raise e


def get_order_by_id(order_id):
    cursor = conn.cursor()
    query = f'''
SELECT * FROM Orders
WHERE id = ?'''
    try:
        cursor.execute(query, (order_id,))
        cursor.close()
        return jsonify(order_fields, trim_order(cursor.fetchone()))
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to fetch order {order_id}\n{e}')
        cursor.close()
        raise e


def get_offers_by_ticker(ticker: str, direction: Direction, price: float = 10000000000000000):
    cursor = conn.cursor()
    query = f'''
SELECT * FROM Orders
WHERE ticker = ? AND direction = ?
AND price <= ?
AND status IN (0, 2)
ORDER BY price ASC, timestamp ASC'''
    sum_query = f'''
SELECT sum(qty) - sum(filled) FROM Orders
WHERE ticker =? AND direction = ?
AND price <= ? AND status IN (0, 2)'''
    try:
        cursor.execute(query, (ticker, int(direction), price))
        offers = [trim_order(jsonify(order_fields, order)) for order in cursor.fetchall()]
        cursor.execute(sum_query, (ticker, int(direction), price))
        total_qty = jsonify(['value'], cursor.fetchone())
        total_qty = total_qty if total_qty['value'] is not None else {'value': 0}
        cursor.close()
        logger.debug(offers)
        return offers, total_qty
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to get offers for ticker {ticker} and direction {direction}\n{e}')
        cursor.close()
        raise e


def cancel_order(order_id):
    cursor = conn.cursor()
    query = f'''
DELETE FROM Orders
WHERE id = ?'''
    try:
        cursor.execute(query, (order_id,))
        cursor.close()
        return True
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to calcel order {order_id}\n{e}')
        cursor.close()
        raise e


def create_market_order(order: MarketOrder, user_id: str):
    cursor = conn.cursor()
    query = f'''
INSERT INTO Orders
(id, status, user_id, timestamp, direction, ticker, qty, type)
VALUES (?, ?, ?, ?, ?, ?, ?, {OrderType.MARKET.value})'''
    try:
        cursor.execute(query, (str(order.id), order.status.value, str(user_id), order.timestamp,
                               order.body.direction.value, order.body.ticker, order.body.qty))
        conn.commit()
        cursor.close()
        return True
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to create order: {order.model_dump()}\n{e}')
        cursor.close()
        raise e


def create_limit_order(order: LimitOrder, user_id: str):
    cursor = conn.cursor()
    query = f'''
INSERT INTO Orders
(id, status, user_id, timestamp, direction, ticker, qty, price, filled, type)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, {OrderType.LIMIT.value})'''
    try:
        cursor.execute(query, (str(order.id), order.status.value, str(user_id), order.timestamp, order.body.direction.value,
                               order.body.ticker, order.body.qty, order.body.price, order.filled))
        conn.commit()
        cursor.close()
        return True
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to create order: {order.model_dump()}\n{e}')
        cursor.close()
        raise e


def update_order_status(order: Union[MarketOrder, LimitOrder], new_status: OrderStatus):
    cursor = conn.cursor()
    query = f'''
UPDATE Orders
SET status = ?
WHERE id = ?'''
    try:
        cursor.execute(query, (new_status.value, str(order.id)))
        conn.commit()
        cursor.close()
        return True
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to update order {order.id} status to {new_status}\n{e}')
        cursor.close()
        raise e


def fill_order(order: Union[MarketOrder, LimitOrder], amount: int):
    cursor = conn.cursor()
    fill_query = f'''
UPDATE Orders
SET filled = filled + ?
WHERE id = ?'''
    unfreeze_query = f'''
UPDATE UserBalance
SET frozen = frozen - ?
WHERE user_id = ?
AND ticker = ?'''
    update_balance(order.user_id, order.body.ticker, -amount, True)
    try:
        cursor.execute(fill_query, (amount, str(order.id)))
        # cursor.execute(unfreeze_query, (amount*order.body.price, str(order.user_id), order.body.ticker))
        conn.commit()
        cursor.close()
        return True
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to increase order {order.id} filled field by {amount}\n{e}')
        cursor.close()
        raise e

transaction_fields = ['id', 'user_id', 'ticker', 'direction',
                      'amount', 'price', 'timestamp']

def get_transactions_by_user(user_id, ticker=None):
    cursor = conn.cursor()
    if ticker:
        ticker = quotify_ticker(ticker)
    query = f'''
SELECT * FROM Transactions
WHERE user_id = ?{f' AND ticker = {ticker}'}'''
    try:
        cursor.execute(query, (str(user_id),))
        response = [jsonify(transaction_fields, transaction) for transaction in cursor.fetchall()]
        cursor.close()
        return response
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to get transactions for user {user_id} {'and ticker ' +ticker if ticker else ''}\n{e}')
        cursor.close()
        raise e


def temp():
    try:
        pass
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to AAAAAA\n{e}')
        raise e


def jsonify(fields: [str], values: Union[list, tuple]) -> {}:
    if len(fields) < 1 or len(values) < 1:
        return None
    count = min(len(fields), len(values))
    result = {}
    for i in range(count):
        result[fields[i]] = values[i]

    return result


# print(
#     'sanya loh'
# )
