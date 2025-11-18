from aaabirzha.schemas import LimitOrderBody, OrderStatus
from schemas import (MarketOrder, LimitOrder, Direction,
                     TransactionBody, Transaction, User)
import database as db_fnc
from datetime import datetime

async def execute_market_order(order: MarketOrder, user: User):
    counter_direction = Direction.BUY if order.body.direction == "SELL" else Direction.SELL
    offers, total_qty = db_fnc.get_offers_by_ticker(order.body.ticker, counter_direction)
    remaining_qty = order.body.qty
    if total_qty < remaining_qty:
        print(f'Failed to execute order {order.id}: not enough standing orders! ({total_qty}/{remaining_qty})')
        return None
    remaining_qty = order.qty
    transactions = []
    for offer in offers:
        offer_order = LimitOrder(
            id = offer['id'],
            status = offer['status'],
            user_id = offer['user_id'],
            body = LimitOrderBody(
                direction = offer['direction'],
                ticker = offer['ticker'],
                qty = offer['qty'],
                price = offer['price']
            ),
            timestamp = offer['timestamp']
        )
        transaction = Transaction(
            user_id = user.id,
            init_order = order.id,
            target_order = offer['id'],
            direction = order.direction,
            body = TransactionBody(
                ticker = order.body.ticker,
                qty = min(offer['qty'], remaining_qty),
                price = offer['price'],
                timestamp = datetime.now()
            )
        )
        peer_id = db_fnc.lookup('Users', 'id', offer['user_id'])['id']
        buy_sell_ids = (user.id, peer_id) if order.body.direction == 'SELL' else (peer_id, user.id)
        if offer['qty'] <= remaining_qty:
            print(f'Order {offer_order.id} executed completely')
            new_status = OrderStatus.EXECUTED
            amount = offer_order.body.qty
        else:
            print(f'Order {offer_order.id} executed partially: the new order is fulfilled')
            new_status = OrderStatus.PART_EXECUTED
            amount = remaining_qty
        print(f'Last transaction: {amount} units executed using order {offer_order.id}. Left to execute: {remaining_qty}')
        db_fnc.decrease_order_qty(offer_order, amount)
        db_fnc.update_order_status(offer_order, new_status)
        remaining_qty -= amount

        db_fnc.exchange_balance(buy_sell_ids[0], buy_sell_ids[1], order.body.ticker, offer['price'], offer['qty'])
        transactions.append(transaction)

        if remaining_qty <= 0:
            print('Order executed completely')
            break

    print(f'Immediate order execution complete. Remaining qty: {remaining_qty}')
    return True


async def execute_limit_order(order: LimitOrder, user: User):
    counter_direction = Direction.BUY if order.body.direction == "SELL" else Direction.SELL
    offers, total_qty = db_fnc.get_offers_by_ticker(order.body.ticker, counter_direction)
    if not offers:
        print('No offers within price margin')
        return False
    else:
        print(f'Commencing immediate partial execution\nStart qty: {order.body.qty} at price {order.body.price}')
        db_fnc.update_order_status(order, OrderStatus.PART_EXECUTED)
    remaining_qty = order.body.qty
    transactions = []
    for offer in offers:
        offer_order = LimitOrder(
            id=offer['id'],
            status=offer['status'],
            user_id=offer['user_id'],
            body=LimitOrderBody(
                direction=offer['direction'],
                ticker=offer['ticker'],
                qty=offer['qty'],
                price=offer['price']
            ),
            timestamp=offer['timestamp']
        )
        transaction = Transaction(
            user_id=user.id,
            init_order=order.id,
            target_order=offer['id'],
            direction=order.direction,
            body=TransactionBody(
                ticker=order.body.ticker,
                qty=min(offer['qty'], remaining_qty),
                price=offer['price'],
                timestamp=datetime.now()
            )
        )
        peer_id = db_fnc.lookup('Users', 'id', offer['user_id'])['id']
        buy_sell_ids = (user.id, peer_id) if order.body.direction == 'SELL' else (peer_id, user.id)
        if offer['qty'] <= remaining_qty:
            print(f'Order {offer_order.id} executed completely')
            new_status = OrderStatus.EXECUTED
            amount = offer_order.body.qty
        else:
            print(f'Order {offer_order.id} executed partially: the new order is fulfilled')
            new_status = OrderStatus.PART_EXECUTED
            amount = remaining_qty
        print(f'Last transaction: {amount} units executed using order {offer_order.id}. Left to execute: {remaining_qty}')
        db_fnc.decrease_order_qty(offer_order, amount)
        db_fnc.update_order_status(offer_order, new_status)
        remaining_qty -= amount

        db_fnc.exchange_balance(buy_sell_ids[0], buy_sell_ids[1], order.body.ticker, offer['price'], offer['qty'])
        transactions.append(transaction)

        if remaining_qty <= 0:
            print('Order executed completely')
            db_fnc.update_order_status(order, OrderStatus.EXECUTED)
            break

    print(f'Immediate order execution complete. Remaining qty: {remaining_qty}')
    return True