import time
import hashlib
import hmac
import json
import datetime

import requests
from btfxwss import BtfxWss
from math import fabs


class Wallet:
    def __init__(self, wallet_data):
        self.wallet_type = wallet_data[0]
        self.currency = wallet_data[1]
        self.balance = wallet_data[2]
        self.unsettled_interest = wallet_data[3]
        self.available_balance = wallet_data[4]
        self.last_change = wallet_data[5]
        self.trade_details = wallet_data[6]


class ActiveOrder(object):
    def __init__(self, order_data):
        self.id = order_data[0]
        self.gid = order_data[1]
        self.cid = order_data[2]
        self.symbol = order_data[3]
        self.mts_create = order_data[4]
        self.mts_update = order_data[5]
        self.amount = order_data[6]
        self.amount_orig = order_data[7]
        self.type = order_data[8]
        self.type_prev = order_data[9]
        self._placeholder = order_data[10]
        self._placeholder = order_data[11]
        self.flags = order_data[12]
        self.status = order_data[13]
        self._placeholder = order_data[14]
        self._placeholder = order_data[15]
        self.price = order_data[16]
        self.price_avg = order_data[17]
        self.price_trailing = order_data[18]
        self.price_aux_limit = order_data[19]
        self._placeholder = order_data[20]
        self._placeholder = order_data[21]
        self._placeholder = order_data[22]
        self.hidden = order_data[23]
        self.placed_id = order_data[24]
        self._placeholder = order_data[25]
        self._placeholder = order_data[26]
        self._placeholder = order_data[27]
        self.routing = order_data[28]
        self._placeholder = order_data[29]
        self._placeholder = order_data[30]
        self.meta = order_data[31]


class HistoricOrder:
    def __init__(self, order_data):
        self.id = order_data[0]
        self.gid = order_data[1]
        self.cid = order_data[2]
        self.symbol = order_data[3]
        self.mts_create = order_data[4]
        self.mts_update = order_data[5]
        self.amount = order_data[6]
        self.amount_orig = order_data[7]
        self.type = order_data[8]
        self.type_prev = order_data[9]
        self.mts_tif = order_data[10]
        self._placeholder = order_data[11]
        self.flags = order_data[12]
        self.order_status = order_data[13]
        self._placeholder = order_data[14]
        self._placeholder = order_data[15]
        self.price = order_data[16]
        self.price_avg = order_data[17]
        self.price_trailing = order_data[18]
        self.price_aux_limit = order_data[19]
        self._placeholder = order_data[20]
        self._placeholder = order_data[21]
        self._placeholder = order_data[22]
        self.notify = order_data[23]
        self.hidden = order_data[24]
        self.placed_id = order_data[25]
        self._placeholder = order_data[26]
        self._placeholder = order_data[27]
        self.routing = order_data[28]
        self._placeholder = order_data[29]
        self._placeholder = order_data[30]
        self.meta = order_data[31]


class Ticker:
    def __init__(self, ticker_data, symbol):
        self.symbol = symbol
        self.bid = ticker_data[0]
        self.bid_size = ticker_data[1]
        self.ask = ticker_data[2]
        self.ask_size = ticker_data[3]
        self.daily_change = ticker_data[4]
        self.daily_change_relative = ticker_data[5]
        self.last_price = ticker_data[6]
        self.volume = ticker_data[7]
        self.high = ticker_data[8]
        self.low = ticker_data[9]


class BFClient(object):
    BASE_URL = "https://api.bitfinex.com/"
    KEY = "dnlaY2ZFpCMtAXUZKVaSpZJ8QPaeHGfEtpd62dWEWHY"
    SECRET = "s4uBAHXLzndrsr7PNemK72PijXeMLHmhYpB8WtsEdcr"
    prices = {}
    wss = BtfxWss()
    _100_days = 100 * 24 * 60 * 60

    def __init__(self, key="", secret="", symbols_set=None, symbol=""):
        self.key = key
        self.secret = secret
        if symbols_set is not None:
            self.wss.start()
            while not self.wss.conn.connected.is_set():
                time.sleep(1)
            self.symbols = symbols_set
            for symbol in symbols_set:
                self.wss.subscribe_to_ticker(symbol[1:])
        if symbol is not None:
            self.asset = symbol[1:4]

    @staticmethod
    def _nonce():
        """
        Returns a nonce
        Used in authentication
        """
        return str(int(round(time.time() * 1000)))

    def _headers(self, path, body):
        nonce = self._nonce()
        signature = "/api/" + path + nonce + json.dumps(body)
        sig = hmac.new(str.encode(self.secret), str.encode(signature), hashlib.sha384).hexdigest()
        return {
            "bfx-nonce": nonce,
            "bfx-apikey": self.key,
            "bfx-signature": sig,
            "content-type": "application/json"
        }

    def get_active_orders(self) -> [ActiveOrder]:
        """
        Fetch active orders
        """
        body = {}
        path = "v2/auth/r/orders"
        _, raw_orders = self._post(path, body)
        resp = []
        for order in raw_orders:
            resp.append(ActiveOrder(order))
        return resp

    def exchange(self, action, price, amount, symbol) -> ActiveOrder:
        if action == "sell":
            amount = -amount
        apiPath = 'v2/auth/w/order/submit'
        body = {
            "type": 'EXCHANGE LIMIT',
            "symbol": symbol,
            "price": str(price),
            "amount": str(amount),
        }
        _, resp = self._post(apiPath, body)
        return ActiveOrder(resp[4][0])

    def _post(self, api_path, body):
        try:
            headers = self._headers(api_path, body)
            r = requests.post(f"https://api.bitfinex.com/{api_path}", json=body, headers=headers)
            if r.status_code != 200:
                print(r.json())
                return False, r.json()
            return True, r.json()
        except TypeError as err:
            print(err)
            return False, err

    @staticmethod
    def _get(api_path, query_params=""):
        try:
            r = requests.get(f"https://api-pub.bitfinex.com/v2/{api_path}?{query_params}")
            if r.status_code != 200:
                print(r.json())
                return False, r.json()
            return True, r.json()
        except TypeError as err:
            print(err)
            return False, err

    def wait_until_order_executed(self, order_id, time_out=_100_days):
        now = datetime.datetime.now
        time_out_time = now() + datetime.timedelta(seconds=time_out)
        order = self.get_active_order(order_id)
        while order is not None:
            order = self.get_active_order(order_id)
            if order is None:
                break
            if now() >= time_out_time:
                return False
            time.sleep(5)
        return True

    def get_ticker(self, symbol):
        ticker_q = self.wss.tickers(symbol[1:])
        if ticker_q.empty():
            return Ticker(self.get_http_ticker(symbol), symbol)
        else:
            last = ""
            while not ticker_q.empty():
                last = ticker_q.get()
            return Ticker(last[0][0], symbol)

    def get_wallet(self, currency):
        apiPath = 'v2/auth/r/wallets'
        body = {}
        _, wallets = self._post(apiPath, body)
        for wallet in wallets:
            if wallet[1] == currency:
                return Wallet(wallet)
        return None

    @staticmethod
    def _extract_order_data(order, resp):
        resp['order_id'] = order[0]
        resp['order_type'] = "BUY" if order[7] > 0 else "SELL"
        resp['order_price'] = order[16]
        resp['order_amount'] = fabs(order[7])
        resp['order_creation'] = datetime.datetime.fromtimestamp(order[4] / 1000.0)
        return resp

    def get_available_asset_amount(self, symbol):
        asset_wallet = self.get_wallet(symbol)
        return asset_wallet.available_balance if asset_wallet is not None else 0

    def get_current_situation(self, symbol):
        asset_available = self.get_available_asset_amount(symbol)
        resp = {"asset_available": asset_available}
        full_filled, active_orders = self.get_active_orders()
        if not full_filled or active_orders is None:
            return None

        if active_orders is not None and len(active_orders) != 0:
            order = active_orders[0]
            resp = self._extract_order_data(order, resp)
            resp['status'] = "ACTIVE ORDER"
            return resp

        past_orders = self.get_orders_history(symbol)
        if past_orders is not None and len(past_orders) != 0:
            last_order_found = False
            index = 0
            while not last_order_found:  # todo
                order_status = past_orders[index].order_status
                if "CANCELED" in order_status:
                    index += 1
                else:
                    last_order_found = True
            last_order = past_orders[index]
            order_status = last_order.order_status
            if "EXECUTED" not in order_status and "INSUFFICIENT BALANCE" not in order_status:
                raise ValueError("Order status is: " + order_status)
            order_type = "BUY" if last_order.amount_orig > 0 else "SELL"
            resp = self._extract_order_data(last_order, resp)
            resp['status'] = "ALL USD" if order_type == "SELL" else "ALL ASSET"
            return resp
        # Case if we are starting clean form zero
        return {
            'status': 'ALL USD',
            'order_price': 0.0,
            'order_amount': 0.0
        }

    def get_orders_history(self, symbol=""):
        if symbol == "":
            path = "v2/auth/r/orders/hist"
        else:
            path = f"v2/auth/r/orders/{symbol}/hist"
        _, raw_orders = self._post(path, {})
        resp = []
        for raw_order in raw_orders:
            resp.append(HistoricOrder(raw_order))
        return resp

    def get_old_order(self, order_id, symbol):
        orders = self.get_orders_history(symbol)
        if orders is None or len(orders) == 0:
            return None
        for order in orders:
            if order.id == order_id:
                return order

    def cancel_order(self, order_id):
        body = {
            "id": order_id
        }
        api_path = "v2/auth/w/order/cancel"
        return self._post(api_path, body)

    def get_active_order(self, order_id):
        orders = self.get_active_orders()
        for order in orders:
            if order.id == order_id:
                return order
        return None

    def get_http_ticker(self, symbol):
        _, ticker = self._get(f"ticker/{symbol}")
        return ticker

    def get_all_tickers(self):
        tickers = {}
        _, resp = self._get("tickers", f"symbols={','.join(self.symbols)}")
        for ticker in resp:
            ticker = Ticker(ticker[1:], ticker[0])
            tickers[ticker.symbol] = ticker
        return tickers


class Test:
    def __init__(self) -> None:
        super().__init__()
        self.bfc = BFClient(["tBTCUSD"])

    def test_get_active_orders(self):
        full_filled, resp = self.bfc.get_active_orders()
        assert full_filled is True
        assert resp is not None
        print(resp)

    def test_exchange(self):
        executed, resp = self.bfc.exchange("buy", 32000, 1, "tBTCUSD")
        print(resp)
        assert executed is False
        assert resp is not None

    def test_get_wallets(self):
        wallet = self.bfc.get_wallet("BTC")
        print(wallet)
        assert wallet is not None

    def test_get_ticker(self):
        ticker = self.bfc.get_ticker("tBTCUSD")
        print(ticker)
        assert ticker is not None


if __name__ == '__main__':
    t = Test()
    # t.test_get_active_orders()
    # t.test_exchange()
    # t.test_get_wallets()
    t.test_get_ticker()
