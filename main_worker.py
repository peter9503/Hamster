import random
import time
import gspread
import os
import numpy as np

from datetime 		import datetime
from binance.spot 	import Spot 
from constant 		import MIN_STEP,currency_pool
from dotenv			import load_dotenv
from decimal		import *

TESTING = False
ONE_SET = 40

def getCurrentBalance(currency, client):	
	ac_data = client.account()

	for b in ac_data["balances"]:
	    if b["asset"] == currency:
	        return b

def sellAll(currency, client):
	sym = currency + "USDT"
	nowq = np.float64(getCurrentBalance(currency, client)["free"])
	l = 1/np.float64(MIN_STEP[currency])
	q = int(nowq * l)/l
	params = {
	    'symbol': sym,
	    'side': 'SELL',
	    'type': 'MARKET',
	    'quantity': q,
	}
	if q == 0:
		return {"state":"nothing to sell"}
	try:
		response = client.new_order(**params)
		tid = response["orderId"]
		response = client.get_order(sym, orderId=tid)
		return {"state":"good","tid":tid, "symbol":sym,"type":"sell","value":response["cummulativeQuoteQty"],"amount":response["executedQty"]}
	except Exception as e:
		print(e)
		return {"state":"sell failed"}
		


def BuyOne(currency, client):
	sym = currency + "USDT"
	q = float(getCurrentBalance("USDT",client)["free"])
	if q <= ONE_SET*2:
		return {"state":"not enough USDT"}

	params = {
	    'symbol': sym,
	    'side': 'BUY',
	    'type': 'MARKET',
	    'quoteOrderQty': ONE_SET,
	}

	response = client.new_order(**params)
	tid = response["orderId"]
	response = client.get_order(sym, orderId=tid)
	return {"state":"good", "tid":tid, "symbol":sym,"type":"buy","value":response["cummulativeQuoteQty"],"amount":response["executedQty"]}

def count_c(sym, client):
    response = client.get_orders(sym)
    response = response[:-1]
    response.reverse()
    out = 0
    counter = 0
    for t in response:
        if t["side"] == "SELL":
            return {"cost":out, "times":counter}
        counter += 1
        out += Decimal(t["cummulativeQuoteQty"])
    return {"cost":out, "times":counter, }

if __name__ == '__main__':
	Json = 'cryptic.json'
	Url = ['https://spreadsheets.google.com/feeds']
	creds = gspread.service_account(filename=Json)
	goo_client = creds.open_by_url("https://docs.google.com/spreadsheets/d/1b6NO0rSUxEZ5ZC6Xc6XMgsFOL8P3YN-S9Uwv6bJCC6A/edit#gid=0")
	timestamp_sheet = goo_client.get_worksheet(0)
	tx_sheet = goo_client.get_worksheet(1)
	p_sheet = goo_client.get_worksheet(2)
	p2w = ['sell','buy']

	load_dotenv()
	pbk = os.getenv('pbk')
	srk = os.getenv('srk')

	print(pbk, srk)

	client = Spot(key= pbk, secret= srk)

	while True:
		curr_t = str(datetime.fromtimestamp(time.time()))
		random.seed(time.time())
		if TESTING:
			P_1 = np.random.poisson(5)
		else:
			P_1 = np.random.poisson(0.5)
		
		if P_1 == 0:
			if TESTING:
				print("timestamp {}".format([curr_t, P_1]))
			else:
				timestamp_sheet.append_row([curr_t, P_1])

		this_round_cur = currency_pool[:]
		
		for i in range(P_1):
			P_2 = random.randint(0,len(this_round_cur)-1)
			P_3 = random.randint(0,1)%2
			cur = this_round_cur[P_2]
			# print(cur, p2w[P_3])
			# i = input()
			if P_3 == 1:
				r = BuyOne(cur, client)

			elif P_3 == 0:
				r = sellAll(cur, client)


			if r["state"] == "good":
				if TESTING:
					print("tx sheet {}".format([curr_t,r["tid"],r["symbol"],r["type"],r["value"],r["amount"]]))
				tx_sheet.append_row([curr_t,r["tid"],r["symbol"],r["type"],r["value"],r["amount"]])
			
			if TESTING:
				print("timestamp {}".format([curr_t, P_1,P_2,cur,P_3,p2w[P_3], r["state"]]))
			timestamp_sheet.append_row([curr_t, P_1,P_2,cur,P_3,p2w[P_3], r["state"]])

			if P_3 == 0 and r["state"] == "good":
				endup = r["value"]
				rr = count_c(r["symbol"], client)
				if TESTING:
					print("profit sheet {}".format([curr_t,r["symbol"],str(rr["cost"]), str(Decimal(r["value"])*Decimal("0.999")), str(Decimal(r["value"]) - Decimal(rr["cost"]) - Decimal(r["value"])*Decimal("0.001")), rr["times"]]))
				p_sheet.append_row([curr_t,r["symbol"],str(rr["cost"]), str(Decimal(r["value"])*Decimal("0.999")), str(Decimal(r["value"]) - Decimal(rr["cost"]) - Decimal(r["value"])*Decimal("0.001")), rr["times"]])

			this_round_cur.remove(cur)

		for i in range(20):
			time.sleep(60)


