import os
import time
from math import fabs
from dotenv import load_dotenv
from BFClient import BFClient, ActiveOrder
from utils import _print

load_dotenv()

trade_fee = 0.001
minimum_gain = 0.005
max_trade_fiat = 100
BF_KEY = os.getenv('BF_KEY')
BF_SECRET = os.getenv('BF_SECRET')
bfc = BFClient()
paths = [
    {"a": "tUSTUSD", "ba": "tBTCUST", "b": "tBTCUSD"},
    {"a": "tUSTUSD", "ba": "tETHUST", "b": "tETHUSD"},
    {"a": "tUSTUSD", "ba": "tDOTUST", "b": "tDOTUSD"},
    {"a": "tUSTUSD", "ba": "tEGLD:UST", "b": "tEGLD:USD"},
    {"a": "tUSTUSD", "ba": "tADAUST", "b": "tADAUSD"},
    {"a": "tUSTUSD", "ba": "tUNIUST", "b": "tUNIUSD"},
    {"a": "tUSTUSD", "ba": "tSUSHI:UST", "b": "tSUSHI:USD"},
]


def calculate_gap(path_tickers, fiat):
    a_price = path_tickers['a'].last_price
    ba_price = path_tickers['ba'].last_price
    b_price = path_tickers['b'].last_price
    forward = fiat / a_price * (b_price / ba_price * (1 - 2 * trade_fee) - a_price * (1 + trade_fee))
    reverse = fiat / b_price * (a_price / (1 / ba_price) * (1 - 2 * trade_fee) - b_price * (1 + trade_fee))
    return forward, reverse


def get_tickers_set():
    tickers_set = {paths[0]['a']}
    for path in paths:
        tickers_set.add(path['ba'])
        tickers_set.add(path['b'])
    return tickers_set


def get_path_tickers(tickers, path):
    return {
        'a': tickers[path['a']],
        'ba': tickers[path['ba']],
        'b': tickers[path['b']]
    }


def forward_vs_revers(forward, reverse, path, path_tickers):
    if forward > reverse:
        return forward, path, path_tickers, False
    else:
        reversed_path = {
            'a': path['b'],
            'ba': path['ba'],
            'b': path['a']
        }
        path_tickers_reversed = {
            'a': path_tickers['b'],
            'ba': path_tickers['ba'],  # todo revisar si tengo invertir el precio o que
            'b': path_tickers['a']
        }
        return reverse, reversed_path, path_tickers_reversed, True


def get_best_gap(tickers, fiat):
    best_gap = best_path = best_path_tickers = best_path_is_reverse = float("-inf")
    for path in paths:
        path_tickers = get_path_tickers(tickers, path)
        forward, reverse = calculate_gap(path_tickers, fiat)
        aux, path, path_tickers, path_is_reverse = forward_vs_revers(forward, reverse, path, path_tickers)
        if aux > best_gap:
            best_gap = aux
            best_path = path
            best_path_tickers = path_tickers
            best_path_is_reverse = path_is_reverse
    return best_gap, best_path, best_path_tickers, best_path_is_reverse


def path_to_string(path, path_tickers):
    # USTUSD(1.001)-ETHUST(1744)-ETHUSD(1770)
    return f"{path['a']}({path_tickers['a'].last_price})-{path['ba']}({path_tickers['ba'].last_price})-{path['b']}({path_tickers['b'].last_price})"


def exchange(action, amount, price, symbol) -> ActiveOrder:
    order = bfc.exchange(action, price, amount, symbol)
    return order


def buy(available_amount, price, symbol) -> ActiveOrder:
    amount = available_amount / price  # todo revisar por qué no matchea con lo que quiero vender
    return exchange("buy", amount, price, symbol)


def sell_all(price, symbol) -> ActiveOrder:
    av_amount = bfc.get_available_asset_amount(symbol)
    return exchange("sell", av_amount, price, symbol)


FIAT = "FIAT"
ASSET = "ASSET"


def get_current_sate():
    past_orders = bfc.get_orders_history()
    last_order = past_orders[0]
    if "USD" in last_order.symbol and last_order.amount > 0:  # bought asset
        return ASSET
    else:  # Sold assets
        return FIAT, ""


def cancel_any_active_order():
    active_orders = bfc.get_active_orders()
    if len(active_orders) > 0:
        bfc.cancel_order(active_orders[0].id)


def execute_abitrage(path, path_tickers, path_is_reverse):
    _print(f"Emitting order for {path['a']}({path_tickers['a'].last_price})")
    order = buy(max_trade_fiat, path_tickers['a'].last_price, path['a'])
    _print(f"Waiting for order {order.id} to execute")
    bfc.wait_until_order_executed(order.id)
    _print(f"Emitting order for {path['ba']}({path_tickers['ba'].last_price})")
    if path_is_reverse:
        order = sell_all(path_tickers['ba'].last_price, path['ba'])
    else:
        order = buy(fabs(order.amount), path_tickers['ba'].last_price, path['ba'])
    _print(f"Waiting for order {order.id} to execute")
    bfc.wait_until_order_executed(order.id)
    _print(f"Emitting order for {path['b']}({path_tickers['b'].last_price})")
    order = sell_all(path_tickers['b'].last_price, path['b'])
    _print(f"Waiting for order {order.id} to execute")
    bfc.wait_until_order_executed(order.id)


def start():
    global bfc
    total_gain = 0
    bfc = BFClient(BF_KEY, BF_SECRET, get_tickers_set())
    _print("Looking for arbitrage opportunities")
    initial_state = get_current_sate()
    cancel_any_active_order()
    while total_gain < 100:
        # if initial_state == FIAT:
        #     _print("All in fiat")
        # elif initial_state == ASSET:
        #     # order = bfc.get_active_orders()
        #     _print("All in asset")
        best_gap, path, path_tickers, path_is_reverse = get_best_gap(bfc.get_all_tickers(), max_trade_fiat)
        while best_gap <= 0:
            best_gap, path, path_tickers, path_is_reverse = get_best_gap(bfc.get_all_tickers(), max_trade_fiat)
            # _print(f"Gap gain=USD${best_gap} on path {path_to_string(path)}")
            print(".", end="")
            time.sleep(1)
        _print(
            f"{'Minimum gap' if best_gap > minimum_gain else 'Positive gap'} found for path {path_to_string(path, path_tickers)} at USD${best_gap}")
        if best_gap > minimum_gain:
            # execute_abitrage(path, path_tickers, path_is_reverse)
            total_gain += best_gap
            # _print(f"Gap filled, total_gain=USD${total_gain}")
    _print(f"Total gain=USD${total_gain}")


if __name__ == '__main__':
    start()
    exit(1)
