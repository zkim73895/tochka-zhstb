from aaabirzha.schemas import LimitOrderBody, OrderStatus
from schemas import (MarketOrder, LimitOrder, Direction,
                     TransactionBody, Transaction, User)
import database as db_fnc
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def execute_market_order(order: MarketOrder, user: User):
    counter_direction = Direction.BUY if order.body.direction == "SELL" else Direction.SELL
    offers, total_qty = db_fnc.get_offers_by_ticker(order.body.ticker, counter_direction)
    remaining_qty = order.body.qty
    if total_qty['value'] < remaining_qty:
        logger.info(f'Failed to execute order {order.id}: not enough standing orders! ({total_qty}/{remaining_qty})')
        return None
    remaining_qty = order.body.qty
    transactions = []
    for offer in offers:
        try:
            offer_order = LimitOrder(
                id = offer['id'],
                status = OrderStatus(offer['status']),
                user_id = offer['user_id'],
                body = {
                    'direction': Direction(offer['direction']),
                    'ticker': offer['ticker'],
                    'qty': offer['qty'],
                    'price': offer['price']
                },
                timestamp = offer['timestamp'],
                filled = offer['filled']
            )
            transaction = Transaction(
                user_id = user.id,
                init_order = order.id,
                target_order = offer['id'],
                direction = order.body.direction,
                body = {
                    'ticker': order.body.ticker,
                    'qty': min(offer['qty'], remaining_qty),
                    'price': offer['price'],
                    'timestamp': datetime.now()
                }
            )
        except Exception as e:
            logger.error(e)
        peer_id = db_fnc.lookup('Users', 'id', offer['user_id'])['id']
        buy_sell_ids = (user.id, peer_id) if order.body.direction == 'SELL' else (peer_id, user.id)
        if offer['qty'] - offer['filled'] <= remaining_qty:
            logger.info(f'Order {offer_order.id} executed completely')
            new_status = OrderStatus.EXECUTED
            amount = offer_order.body.qty - offer['filled']
        else:
            logger.info(f'Order {offer_order.id} executed partially: the new order is fulfilled')
            new_status = OrderStatus.PART_EXECUTED
            amount = remaining_qty
        logger.info(f'Last transaction: {amount} units executed using order {offer_order.id}. Left to execute: {remaining_qty}')
        db_fnc.fill_order(offer_order, amount)
        db_fnc.update_order_status(offer_order, new_status)
        remaining_qty -= amount

        db_fnc.exchange_balance(buy_sell_ids[0], buy_sell_ids[1], order.body.ticker, offer['price'], amount)
        transactions.append(transaction)

        if remaining_qty <= 0:
            logger.info('Order executed completely')
            break

    logger.info(f'Immediate order execution complete. Remaining qty: {remaining_qty}')
    return True


async def execute_limit_order(order: LimitOrder, user: User):
    counter_direction = Direction.BUY if order.body.direction.name == "SELL" else Direction.SELL
    offers, total_qty = db_fnc.get_offers_by_ticker(order.body.ticker, counter_direction)
    remaining_qty = order.body.qty
    transactions = []
    if not offers:
        logger.info('No offers within price margin')
    else:
        logger.info(f'Commencing immediate partial execution\nStart qty: {order.body.qty} at price {order.body.price}')
        db_fnc.update_order_status(order, OrderStatus.PART_EXECUTED)
        for offer in offers:
            offer_order = LimitOrder(
                id=offer['id'],
                status=offer['status'],
                user_id=offer['user_id'],
                body = {
                        'direction': Direction(offer['direction']),
                        'ticker': offer['ticker'],
                        'qty': offer['qty'],
                        'price': offer['price']
                    },
                timestamp=offer['timestamp'],
                filled=offer['filled']
            )
            transaction = Transaction(
                user_id=user.id,
                init_order=order.id,
                target_order=offer['id'],
                direction=order.body.direction,
                body= {
                    'ticker': order.body.ticker,
                    'qty': min(offer['qty'], remaining_qty),
                    'price': offer['price'],
                    'timestamp': datetime.now()
                }
            )
            peer_id = db_fnc.lookup('Users', 'id', offer['user_id'])['id']
            buy_sell_ids = (user.id, peer_id) if order.body.direction == 'SELL' else (peer_id, user.id)
            if offer['qty'] - offer['filled'] <= remaining_qty:
                logger.info(f'Order {offer_order.id} executed completely')
                new_status = OrderStatus.EXECUTED
                amount = offer_order.body.qty - offer['filled']
            else:
                logger.info(f'Order {offer_order.id} executed partially: the new order is fulfilled')
                new_status = OrderStatus.PART_EXECUTED
                amount = remaining_qty
            logger.info(f'Last transaction: {amount} units executed using order {offer_order.id}. Left to execute: {remaining_qty}')
            db_fnc.fill_order(offer_order, amount)
            db_fnc.update_order_status(offer_order, new_status)
            remaining_qty -= amount

            db_fnc.exchange_balance(buy_sell_ids[0], buy_sell_ids[1], order.body.ticker, offer['price'], amount)
            transactions.append(transaction)

            if remaining_qty <= 0:
                logger.info('Order executed completely')
                db_fnc.update_order_status(order, OrderStatus.EXECUTED)
                break

    to_freeze = remaining_qty*order.body.price if order.body.direction == Direction.BUY else remaining_qty
    freeze_ticker = 'RUB' if order.body.direction == Direction.BUY else order.body.ticker
    db_fnc.update_balance(user.id, freeze_ticker, to_freeze, is_freeze=True)
    logger.info(f'''Immediate order execution complete. Remaining qty: {remaining_qty}/{order.body.qty}
{to_freeze} of RUB frozen for the {remaining_qty} units of {order.body.ticker} at {order.body.price} a unit''')
    return True