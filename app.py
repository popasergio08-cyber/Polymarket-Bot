import os, json
from flask import Flask, request, jsonify
from py_clob_client_v2 import ClobClient, OrderArgs
from py_clob_client_v2.order_builder.constants import BUY

app = Flask(__name__)

PRIVATE_KEY = os.getenv('PRIVATE_KEY')
[REDACTED]
[REDACTED]
PASSPHRASE = os.getenv('PASSPHRASE')
WALLET = os.getenv('WALLET_ADDRESS')

client = ClobClient(
    host='https://clob.polymarket.com',
    chain_id=137,
    key=PRIVATE_KEY,
    creds={'apiKey': API_KEY, 'secret': SECRET, 'passphrase': PASSPHRASE},
    signature_type=1,
    funder=WALLET
)

@app.route('/')
def health():
    return jsonify({'status': 'ok'})

@app.route('/order', methods=['POST'])
def place_order():
    try:
        data = request.get_json(force=True)
        token_id = str(data['tokenId'])
        price = float(data['price'])
        amount = float(data['amount'])
        size = round(amount / price, 2)
        result = client.create_and_post_order(
            OrderArgs(token_id=token_id, price=price, size=size, side=BUY)
        )
        order_id = result.get('orderID', 'N/A') if isinstance(result, dict) else 'N/A'
        return jsonify({'success': True, 'orderID': order_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
