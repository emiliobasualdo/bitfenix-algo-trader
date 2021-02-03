import time
import hashlib
import hmac
import json
import datetime

import requests
from btfxwss import BtfxWss
from math import fabs


class BFClient(object):
    BASE_URL = "https://api.bitfinex.com/"
    KEY = "0jUlwsazd1gKlkAGcRDhlu1kdKCsAxw6MGWie0qsLNm"
    SECRET = "g3pPZnnRvFfWKSYM08Z62vmPFWEVy2jjRY3jN8j7UfI"
    prices = {}
    wss = BtfxWss()
    _100_days = 100 * 24 * 60 * 60
    def __init__(self, ticker):
        self.wss.start()
        while not self.wss.conn.connected.is_set():
            time.sleep(1)
        self.wss.subscribe_to_ticker(ticker)

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
        sig = hmac.new(str.encode(self.SECRET), str.encode(signature), hashlib.sha384).hexdigest()
        return {
            "bfx-nonce": nonce,
            "bfx-apikey": self.KEY,
            "bfx-signature": sig,
            "content-type": "application/json"
        }

    def get_active_orders(self):
        """
        Fetch active orders
        """
        body = {}
        path = "v2/auth/r/orders"
        return self.post(path, body)

    def exchange(self, action, price, amount, ticker):
        if action == "sell":
            amount = -amount
        apiPath = 'v2/auth/w/order/submit'
        body = {
            "type": 'EXCHANGE LIMIT',
            "symbol": ticker,
            "price": str(price),
            "amount": str(amount),
        }
        submitted, resp = self.post(apiPath, body)
        if not submitted or resp is None:
            return False, resp
        return True, resp

    def post(self, api_path, body):
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

    def wait_until_order_executed(self, order_id, time_out=_100_days):
        now = datetime.datetime.now
        time_out_time = now() + datetime.timedelta(seconds=time_out)
        order_still_pending = True
        while order_still_pending:
            order_still_pending = False
            full_filled, orders = self.get_active_orders()
            if full_filled is not True or orders is None or len(orders) == 0:
                return False
            for order in orders:
                if order[0] == order_id:
                    order_still_pending = True
                    break
            if now() >= time_out_time and order_still_pending:
                return False
            if order_still_pending:
                time.sleep(5)
        return True

    def get_price(self, ticker):
        ticker_q = self.wss.tickers(ticker)
        while ticker_q.empty():
            time.sleep(1)
            ticker_q = self.wss.tickers(ticker)
        last = ""
        while not ticker_q.empty():
            last = ticker_q.get()
        return last[0][0][6]

    def get_wallet(self, currency):
        apiPath = 'v2/auth/r/wallets'
        body = {}
        _, wallets = self.post(apiPath, body)
        for wallet in wallets:
            if wallet[1] == currency:
                return wallet
        return None

    @staticmethod
    def _extract_order_data(order, resp):
        resp['order_id'] = order[0]
        resp['order_type'] = "BUY" if order[7] > 0 else "SELL"
        resp['order_price'] = order[16]
        resp['order_amount'] = fabs(order[7])
        resp['order_creation'] = datetime.datetime.fromtimestamp(order[4] / 1000.0)
        return resp


    def get_current_situation(self):
        btc_wallet = self.get_wallet("BTC")
        btc_available = btc_wallet[4] if btc_wallet is not None else 0
        resp = {"btc_available": btc_available}
        full_filled, active_orders = self.get_active_orders()
        if not full_filled or active_orders is None:
            return None

        if active_orders is not None and len(active_orders) != 0:
            order = active_orders[0]
            resp = self._extract_order_data(order, resp)
            resp['status'] = "ACTIVE ORDER"
            return resp

        full_filled, past_orders = self.get_orders_history()
        if not full_filled:
            return None
        if past_orders is not None and len(past_orders) != 0:
            last_order_found = False
            index = 0
            while not last_order_found: # todo
                order_status = past_orders[index][13]
                if "CANCELED" in order_status:
                    index += 1
                else:
                    last_order_found = True
            last_order = past_orders[index]
            order_status = last_order[13]
            if "EXECUTED" not in order_status and "INSUFFICIENT BALANCE" not in order_status:
                raise ValueError("Order status is: " + order_status)
            order_type = "BUY" if last_order[7] > 0 else "SELL"
            resp = self._extract_order_data(last_order, resp)
            resp['status'] = "ALL USD" if order_type == "SELL" else "ALL BTC"
            return resp
        # Case if we are starting clean form zero
        return {
            'status': 'ALL USD',
            'order_price': 0.0,
            'order_amount': 0.0
        }

    def get_orders_history(self):
        return self.post("v2/auth/r/orders/tBTCUSD/hist", {})

    def cancel_order(self, order_id):
        body = {
            "id": order_id
        }
        api_path = "v2/auth/w/order/cancel"
        return self.post(api_path, body)


class Test:
    def __init__(self) -> None:
        super().__init__()
        self.bfc = BFClient("BTCUSD")

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


if __name__ == '__main__':
    t = Test()
    #t.test_get_active_orders()
    #t.test_exchange()
    t.test_get_wallets()