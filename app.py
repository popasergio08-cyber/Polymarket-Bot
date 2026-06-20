from flask import Flask,request,jsonify
from py_clob_client_v2 import ClobClient,OrderArgs
from py_clob_client_v2.order_builder.constants import BUY
import os
app=Flask(__name__)
client=ClobClient(host='https://clob.polymarket.com',chain_id=137,key=os.getenv('PRIVATE_KEY'),creds={'apiKey':os.getenv('API_KEY'),'secret':os.getenv('SECRET'),'passphrase':os.getenv('PASSPHRASE')},signature_type=1,funder=os.getenv('WALLET_ADDRESS'))
@app.route('/order',methods=['POST'])
def order():
 d=request.json
 price=float(d['price'])
 size=round(float(d['amount'])/price,2)
 r=client.create_and_post_order(OrderArgs(token_id=d['tokenId'],price=price,size=size,side=BUY))
 return jsonify({'success':True,'orderID':r.get('orderID',''),'status':r.get('status','')})
@app.route('/')
def health():
 return 'ok'
if __name__=='__main__':
 app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)))
