from BFClient import BFClient
from math import floor, log10, fabs
from datetime import datetime
import time
import argparse

parser = argparse.ArgumentParser(description='Gain some money!')
parser.add_argument('max_fiat', type=float)  # 100.0 tBTCUSD 10 1.0
parser.add_argument('symbol', type=str)  # tBTCUSD
parser.add_argument('price_interval_seconds', type=int)  # 10
parser.add_argument('minimum_gain', type=float)  # 10

args = parser.parse_args()

max_fiat = args.max_fiat
symbol = args.symbol
price_interval_sleep = args.price_interval_seconds
minimum_gain = args.minimum_gain
trade_fee = 0.002

bfc = BFClient()

ALL_USD = "ALL_USD"
WAIT_BUY_EXECUTION = "WAIT_BUY_EXECUTION"
SEARCH_FOR_SELL_WINDOW = "SEARCH_FOR_SELL_WINDOW"
WAIT_SELL_EXECUTION = "WAIT_SELL_EXECUTION"
WAIT_FOR_PRICE_TO_DROP = "WAIT_FOR_PRICE_TO_DROP"


def get_state():
    initial_situation = bfc.get_current_situation()
    order_id = 0
    state = ""
    if initial_situation['status'] == "ACTIVE ORDER":
        order_id = initial_situation['order_id']
        if initial_situation["order_type"] == "BUY":
            state = WAIT_BUY_EXECUTION
        else:
            state = WAIT_SELL_EXECUTION
    else:
        if initial_situation['status'] == "ALL USD":
            state = ALL_USD
        else:
            state = SEARCH_FOR_SELL_WINDOW
    last_bought_price = initial_situation['order_price']
    last_bought_amount = initial_situation['order_amount']
    return state, order_id, last_bought_price, last_bought_amount

def _print(str=""):
    print(datetime.now().strftime("%d/%m %H:%M:%S "), str)

def _round(num):
    return round(round(num, 8), 5-int(floor(log10(fabs(num))))-1)

def buy(volume):
    price = _round(bfc.get_price(symbol) * 0.99999)
    amount = _round(volume/ price)
    fee = price * amount * trade_fee
    _print(f"Placing buy order for {amount} BTC at USD${price} paying USD${fee} fee")
    _, resp = bfc.exchange("buy", price, amount, symbol)
    return price, amount, fee, resp[4][0][0]


def sell(price, amount):
    price = _round(price)
    amount = _round(amount)
    fee = price * amount * trade_fee
    _print(f"Placing sell order for {amount} BTC at USD${price} paying USD${fee} fee")
    _, resp = bfc.exchange("sell", price, amount, symbol)
    return price, amount, fee, resp[4][0][0]


def start():
    _print()
    total_gain = total_fees = cycle_fees = order_id = 0
    state, order_id, last_bought_price, last_bought_amount = get_state()
    fiat_available = max_fiat
    while total_gain < 500:
        if state == ALL_USD:
            # We buy as much as we can
            last_bought_price, last_bought_amount, fee, order_id = buy(fiat_available)
            cycle_fees += fee
            state = WAIT_BUY_EXECUTION
        elif state == WAIT_BUY_EXECUTION:
            _print(f"Waiting for buy order {order_id} to execute")
            bfc.wait_until_order_executed(order_id)
            _print(f"Order executed")
            state = SEARCH_FOR_SELL_WINDOW
        elif state == SEARCH_FOR_SELL_WINDOW:
            minimum_sell_price = _round((minimum_gain + fiat_available*(1+trade_fee)) / (last_bought_amount*(1-trade_fee)))
            _print(f"Waiting for sell window >=USD${minimum_sell_price}")
            ticker_value = bfc.get_price(symbol)
            while ticker_value < minimum_sell_price:
                time.sleep(price_interval_sleep)
                ticker_value = bfc.get_price(symbol)
            if ticker_value == minimum_sell_price:
                sell_price = minimum_sell_price
            else:  # ticker_value > minimum_sell_price:
                sell_price = ticker_value

            last_bought_price, last_bought_amount, fee, order_id = sell(sell_price, last_bought_amount)
            cycle_fees += fee
            gain = last_bought_amount * last_bought_price - fiat_available - cycle_fees
            total_gain += gain
            total_fees += cycle_fees
            _print(f"Cylce gain=USD${gain} total_gain=USD{total_gain} cycle_fee=USD{cycle_fees} total_fees=USD{total_fees}")
            state = WAIT_SELL_EXECUTION
        elif WAIT_SELL_EXECUTION:
            _print(f"Waiting for sell order {order_id} to execute")
            bfc.wait_until_order_executed(order_id)
            _print("Order executed")
            state = WAIT_FOR_PRICE_TO_DROP
        elif WAIT_FOR_PRICE_TO_DROP:
            # We will wait a maximum of 5 minutes
            seconds_left = 5 * 60
            ticker_value = bfc.get_price(symbol)
            while seconds_left > 0 and ticker_value >= last_bought_price:
                time.sleep(price_interval_sleep)
                seconds_left -= price_interval_sleep
                ticker_value = bfc.get_price(symbol)
            if seconds_left > 0:
                _print(f"Found price drop at=USD{ticker_value}")
            else:
                _print("Price drop timeout")
            state = ALL_USD

if __name__ == '__main__':
    start()