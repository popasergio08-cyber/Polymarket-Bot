import os,time,requests,threading
from flask import Flask,request,jsonify
from py_clob_client_v2 import ClobClient,OrderArgs
from py_clob_client_v2.order_builder.constants import BUY

app=Flask(__name__)

PRIVATE_KEY=os.getenv('PRIVATE_KEY')
[REDACTED]
[REDACTED]
PASSPHRASE=os.getenv('PASSPHRASE')
WALLET=os.getenv('WALLET_ADDRESS')
TELEGRAM_TOKEN=os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT=os.getenv('TELEGRAM_CHAT')
client=ClobClient(host='https://clob.polymarket.com',chain_id=137,key=PRIVATE_KEY,creds={'apiKey':API_KEY,'secret':SECRET,'passphrase':PASSPHRASE},signature_type=1,funder=WALLET)

state={'upReached58':False,'downReached58':False,'upBought':False,'downBought':False,'lastMarketId':''}

def notify(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT:
        try:
            requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',json={'chat_id':TELEGRAM_CHAT,'text':msg},timeout=5)
        except:pass

def get_market():
    try:
        r=requests.get('https://gamma-api.polymarket.com/markets',params={'active':'true','closed':'false','slug_search':'btc-updown-15m','limit':'1'},timeout=5)
        data=r.json()
        if isinstance(data,list) and len(data)>0:return data[0]
        if isinstance(data,dict) and 'data' in data and len(data['data'])>0:return data['data'][0]
    except:pass
    return None
 def place_order(token_id,price,amount,label,reason):
    try:
        size=round(amount/price,2)
        r=client.create_and_post_order(OrderArgs(token_id=token_id,price=price,size=size,side=BUY))
        oid=r.get('orderID','N/A') if isinstance(r,dict) else 'N/A'
        notify(f'ORDINE ESEGUITO\nLato: {label}\nImporto: {amount}euro\nQuota: {int(price*100)}c\nMotivo: {reason}\nID: {oid}')
        return True
    except Exception as e:
        notify(f'ERRORE ORDINE {label}: {str(e)}')
        return False

def monitor():
    global state
    while True:
        try:
            m=get_market()
            if not m:
                time.sleep(1)
                continue
            import json
            outcomes=json.loads(m.get('outcomes','[]'))
            prices=json.loads(m.get('outcomePrices','[]'))
            tokens=json.loads(m.get('clobTokenIds','[]'))
            if len(outcomes)<2 or len(prices)<2:
                time.sleep(1)
                continue
ui=outcomes.index('Up') if 'Up' in outcomes else 0
            di=outcomes.index('Down') if 'Down' in outcomes else 1
            up=float(prices[ui])
            dn=float(prices[di])
            ut=tokens[ui]
            dt=tokens[di]
            mid=m.get('id',m.get('slug',''))
            if state['lastMarketId']!=mid:
                state={'upReached58':False,'downReached58':False,'upBought':False,'downBought':False,'lastMarketId':mid}
            if up>=0.58:state['upReached58']=True
            if dn>=0.58:state['downReached58']=True
            if up>=0.58 and not state['upBought']:
                place_order(ut,up,2,'UP','UP>=58c acquisto 2euro')
                state['upBought']=True
                if dn>=0.34 and not state['downBought']:
                    place_order(dt,dn,1,'DOWN','DOWN>=34c con UP@58 acquisto 1euro')
                    state['downBought']=True
            if dn>=0.58 and not state['downBought']:
                place_order(dt,dn,2,'DOWN','DOWN>=58c acquisto 2euro')
                state['downBought']=True
                if up>=0.34 and not state['upBought']:
                    place_order(ut,up,1,'UP','UP>=34c con DOWN@58 acquisto 1euro')
                    state['upBought']=True
            if state['upReached58'] and up<0.58 and state['upBought'] and not state['downBought'] and dn>=0.50:
                place_order(dt,dn,1,'DOWN','UP era@58 poi sceso DOWN a 50c acquisto 1euro')
             state['downBought']=True
            if state['downReached58'] and dn<0.58 and state['downBought'] and not state['upBought'] and up>=0.50:
                place_order(ut,up,2,'UP','DOWN era@58 poi scesa UP a 50c acquisto 2euro')
                state['upBought']=True
        except Exception as e:
            print(f'Monitor error: {e}')
        time.sleep(1)

threading.Thread(target=monitor,daemon=True).start()

@app.route('/')
def health():
    return jsonify({'status':'ok','state':state})

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)))
