import sqlite3 as sql
import logging

from aaabirzha.schemas import Direction
from schemas import MarketOrder, LimitOrder, OrderType, OrderStatus
from typing import Union


conn = sql.connect('database.db')

conn.execute('PRAGMA journal_mode=WAL;')

main_cursor = conn.cursor()

logger = logging.getLogger(__name__)


def create_user(id, name, role, api_key_hashed, api_key=None):
    cursor = conn.cursor()
    query = f'''
    INSERT INTO Users (id, name, role, api_key_hashed, api_key)
    VALUES (?, ?, ?, ?, ?);
    '''
    try:
        cursor.execute(query, (str(id), name, int(role), api_key_hashed, api_key))
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
    try:
        cursor.execute(query, (ticker))
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


def update_balance(user_id, ticker, amount: int, is_deposit: bool):
    cursor = conn.cursor()
    user_id = str(user_id)

    logger.debug(f'''user_id:{user_id}
ticker: {ticker}
amount: {amount}
type: {'deposit' if is_deposit else 'withdraw'}''')

    balance = lookup_balance(user_id, ticker)

    logger.debug(f'Balance: {balance}')

    if not balance:
        logger.info(f'User {user_id} does not have a {ticker} balance')
        if is_deposit:
            new_ticker(user_id, ticker)
            logger.info(f'{ticker} balance created')
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
        logger.info(f'''Transaction made. Type is deposit: {is_deposit}
        User: {user_id}
        Ticker {ticker} balance updated from {balance} to {balance + amount}''')
        conn.commit()
    except sql.DatabaseError as e:
        logger.error(f'Failed to add ticker {ticker} to user {user_id}\n{e}')
    cursor.close()


def exchange_balance(buyer_id, seller_id, ticker, price: float, amount: int):
    try:
        conn.execute('BEGIN TRANSACTION')
        update_balance(buyer_id, ticker, amount, True)
        update_balance(seller_id, 'RUB', int(amount*price), True)
        update_balance(seller_id, ticker, amount, False)
        update_balance(buyer_id, 'RUB', int(amount * price), False)
        conn.execute('COMMIT')

    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to get all instruments\n{e}')
        conn.execute('ROLLBACK')


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
        logger.info(f'Trying to look up balance of all instruments for user {user_id}')

        cursor.execute(query, (user_id,))
        response = cursor.fetchall()
        return response

    query = f'''
    SELECT balance FROM UserBalance 
    WHERE user_id = ? AND ticker = ?
    '''

    logger.info(f'Trying to look up {ticker} balance for {user_id}\nQuery:\n{query}')

    cursor.execute(query, (user_id, ticker))
    response = cursor.fetchone()

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


def get_orders_for_user(user_id, ticker=None):
    cursor = conn.cursor()
    query = f'''
SELECT * FROM Orders
WHERE user_id = ?{f' AND ticker = {ticker}' if ticker else ''}'''
    try:
        cursor.execute(query, (str(user_id),))
        response = [trim_order(order) for order in cursor.fetchall()]
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
        return trim_order(cursor.fetchone())
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
AND state IN (0, 2)
ORDER BY price ASC, timestamp ASC'''
    sum_query = f'''
SELECT sum(qty) - sum(filled) FROM Orders
WHERE ticker =? AND direction = ?
AND price <= ? AND state IN (0, 2)'''
    try:
        cursor.execute(query, (ticker, int(direction), price))
        offers = [trim_order(order) for order in cursor.fetchall()]
        cursor.execute(sum_query, (ticker, int(direction), price))
        total_qty = cursor.fetchone()
        cursor.close()
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


def create_market_order(order: MarketOrder):
    cursor = conn.cursor()
    query = f'''
INSERT INTO Orders
(id, status, user_id, timestamp, direction, ticker, qty, type)
VALUES (?, ?, ?, ?, ?, ?, ?, {OrderType.MARKET})'''
    try:
        cursor.execute(query, (order.id, order.status, order.timestamp, order.direction, order.ticker, order.qty))
        cursor.close()
        return True
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to create order: {order.model_dump()}\n{e}')
        cursor.close()
        raise e


def create_limit_order(order: LimitOrder):
    cursor = conn.cursor()
    query = f'''
INSERT INTO LimitOrders
(id, status, user_id, timestamp, direction, ticker, qty, price, filled, type)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, {OrderType.LIMIT})'''
    try:
        cursor.execute(query, (order.id, order.status, order.timestamp, order.direction, order.ticker,
                               order.qty, order.price, order.filled))
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
        cursor.execute(query, (new_status, order.id))
        cursor.close()
        return True
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to update order {order.id} status to {new_status}\n{e}')
        cursor.close()
        raise e


def decrease_order_qty(order: Union[MarketOrder, LimitOrder], decrement: int):
    cursor = conn.cursor()
    query = f'''
UPDATE Orders
SET qty = qty - ?
WHERE id = ?'''
    try:
        cursor.execute(query, (decrement, order.id))
        cursor.close()
        return True
    except sql.DatabaseError as e:
        logger.error(f'DBError: Failed to decrement order {order.id} qty by {decrement}\n{e}')
        cursor.close()
        raise e


def get_transactions_by_user(user_id, ticker=None):
    cursor = conn.cursor()
    query = f'''
SELECT * FROM Transactions
WHERE user_id = ?{f' AND ticker = {ticker}'}'''
    try:
        cursor.execute(query, (user_id,))
        cursor.close()
        return cursor.fetchall()
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
