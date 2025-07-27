from trader import Trader

trad = Trader()
print(trad.exchange.futures_exchange_info()['symbols'])
