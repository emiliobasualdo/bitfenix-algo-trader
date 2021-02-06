from BFClient import BFClient
from math import floor, log10, fabs
from datetime import datetime, timedelta
import time
import argparse

parser = argparse.ArgumentParser(description='Gain some money!')
parser.add_argument('max_fiat', type=float)  # 100.0 tBTCUSD 10 1.0
parser.add_argument('symbol', type=str)  # tBTCUSD
parser.add_argument('price_interval_seconds', type=int)  # 10
parser.add_argument('minimum_gain', type=float)  # 0.1

args = parser.parse_args()

max_fiat = args.max_fiat
symbol = args.symbol
price_interval_sleep = args.price_interval_seconds
minimum_gain = args.minimum_gain
trade_fee = 0.002
ticker = symbol[1:]  # tBTCUSD -> BTCUSD
_5_hours = 5 * 60 * 60
sell_order_timeout_mill = _5_hours * 1000

bfc = BFClient(ticker)

ALL_USD = "ALL_USD"
WAIT_BUY_EXECUTION = "WAIT_BUY_EXECUTION"
SUBMIT_SELL_ORDER = "SUBMIT_SELL_ORDER"
WATCH_SELL_ORDER = "WAIT_SELL_EXECUTION"
WAIT_FOR_PRICE_TO_DROP = "WAIT_FOR_PRICE_TO_DROP"

def get_state():
    initial_situation = bfc.get_current_situation()
    order_id = 0
    if initial_situation['status'] == "ACTIVE ORDER":
        order_id = initial_situation['order_id']
        if initial_situation["order_type"] == "BUY":
            state = WAIT_BUY_EXECUTION
        else:
            state = WATCH_SELL_ORDER
    else:
        if initial_situation['status'] == "ALL USD":
            state = ALL_USD
        else:
            state = SUBMIT_SELL_ORDER
    last_bought_price = initial_situation['order_price']
    last_bought_amount = initial_situation['order_amount']
    order_creation = initial_situation['order_creation']
    btc_available_amount = initial_situation['btc_available']
    return state, order_id, last_bought_price, last_bought_amount, order_creation, btc_available_amount

def _print(str=""):
    print(datetime.now().strftime("%d/%m %H:%M:%S "), str)

def _round(num):
    return round(round(num, 8), 5-int(floor(log10(fabs(num))))-1)

tickers = {}
def set_ticker(_ticker, price):
    tickers[_ticker] = price

def buy(volume):
    price = _round(bfc.get_price(ticker) * 0.9999999)
    amount = volume / price  # amount does not need to be rounded
    fee = price * amount * trade_fee
    _print(f"Placing buy order for {amount} BTC at USD${price} paying USD${fee} fee")
    _, resp = bfc.exchange("buy", price, amount, symbol)
    return price, amount, fee, resp[4][0][0]


def sell(price, amount):
    price = _round(price)
    amount = amount  # amount does not need to be rounded
    fee = price * amount * trade_fee
    _print(f"Placing sell order for {amount} BTC at USD${price} paying USD${fee} fee")
    _, resp = bfc.exchange("sell", price, amount, symbol)
    order_id = resp[4][0][0]
    order_creation = resp[4][0][4]
    return price, amount, fee, order_id, order_creation

def reduce_gain(gain):
    return round(gain - gain/10, 5)

def start():
    _print()
    total_gain = total_fees = cycle_fees = fee = 0
    state, order_id, last_bought_price, last_bought_amount, order_creation, btc_available_amount = get_state()
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
            state = SUBMIT_SELL_ORDER
        elif state == SUBMIT_SELL_ORDER:
            _, _, _, _, _, btc_available_amount = get_state()
            minimum_sell_price = (minimum_gain + fiat_available*(1+trade_fee)) / (btc_available_amount*(1-trade_fee))
            minimum_sell_price = _round(minimum_sell_price)
            ticker_value = bfc.get_price(ticker)
            # if we come back ten days later an the price is higher than our minimum, we sell to the higher price
            if ticker_value > minimum_sell_price:
                sell_price = ticker_value
            else:
                sell_price = minimum_sell_price
            last_bought_price, last_bought_amount, fee, order_id, order_creation = sell(sell_price, btc_available_amount)
            state = WATCH_SELL_ORDER
        elif state == WATCH_SELL_ORDER:
            # if we come back ten days later, we cancel the order and emmit a new order to an adjusted minimum price
            if time.time() - order_creation > sell_order_timeout_mill:
                _print(f"Waiting for sell order {order_id} to execute")
                bfc.cancel_order(order_id)
                state = SUBMIT_SELL_ORDER
                break
            _print(f"Waiting for sell order {order_id} to execute")
            bfc.wait_until_order_executed(order_id)
            _print("Order executed")
            cycle_fees += fee
            gain = last_bought_amount * last_bought_price - fiat_available - cycle_fees
            total_gain += gain
            total_fees += cycle_fees
            _print(f"Cycle gain=USD${gain} total_gain=USD{total_gain} cycle_fee=USD{cycle_fees} total_fees=USD{total_fees}")
            state = WAIT_FOR_PRICE_TO_DROP
        elif state == WAIT_FOR_PRICE_TO_DROP:
            # We will wait a maximum of 5 minutes
            seconds_left = 5 * 60
            ticker_value = bfc.get_price(ticker)
            while seconds_left > 0 and ticker_value >= last_bought_price:
                time.sleep(price_interval_sleep)
                seconds_left -= price_interval_sleep
                ticker_value = bfc.get_price(ticker)
            if seconds_left > 0:
                _print(f"Found price drop at=USD{ticker_value}")
            else:
                _print("Price drop timeout")
            state = ALL_USD
    _print(f"Exiting state={state} total_gain={total_gain} total_fees={total_fees}")
    exit(0)

if __name__ == '__main__':
    start()