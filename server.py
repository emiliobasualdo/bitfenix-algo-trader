from multiprocessing.connection import Listener
import _thread
import requests
import time
import sys
from BFClient import BFClient

prices = {}
ticker_request_interval = 10
bfc = BFClient()



def execute_action(action_args):
    action = action_args[0]
    if action == "ticker":
        return prices[action_args[1]]
    elif action == "buy" or action == "sell":
        return bfc.exchange(action_args[0], action_args[1], action_args[2], action_args[3])


def conn_price_return():
    while True:
        conn = listener.accept()
        print('connection accepted from', listener.last_accepted)
        while True:
            try:
                action_args = conn.recv()
                resp = execute_action(action_args)
                conn.send(resp)
            except:
                a = sys.exc_info()
                print("Unexpected error:", a)
                break


if __name__ == '__main__':
    address = ('localhost', 6000)
    listener = Listener(address)
    print(f"Server listening on {address}")
    try:
        _thread.start_new_thread(conn_price_return, ())
    except:
        print("Error: unable to start thread")

    get_prices()
