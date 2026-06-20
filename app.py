import os, json, time, threading, requests
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

latest_prices = {
    'upPrice': 0, 'downPrice': 0,
    'upTokenId': '', 'downTokenId': '',
    'marketSlug': '', 'marketId': '',
    'endDate': '', 'conditionId': '',
    'updatedAt': 0
}

def fetch_prices():
    while True:
        try:
            now = time.time()
            block_sec = int(now // 900) * 900
            slug = f'btc-updown-15m-{block_sec}'
            r = requests.get(
                'https://gamma-api.polymarket.com/markets',
                params={'slug': slug, 'active': 'true', 'limit': '5'},
                timeout=5
            )
            markets = r.json()
            if isinstance(markets, dict):
                markets = markets.get('data', [])
            for m in markets:
                outcomes = json.loads(m.get('outcomes', '[]'))
                if 'Up' in outcomes and 'Down' in outcomes:
                    prices = json.loads(m.get('outcomePrices', '[]'))
                    tokens = json.loads(m.get('clobTokenIds', '[]'))
                    up_idx = outcomes.index('Up')
                    dn_idx = outcomes.index('Down')
                    latest_prices['upPrice'] = float(prices[up_idx])
                    latest_prices['downPrice'] = float(prices[dn_idx])
                    latest_prices['upTokenId'] = tokens[up_idx]
                    latest_prices['downTokenId'] = tokens[dn_idx]
                    latest_prices['marketSlug'] = m.get('slug', '')
                    latest_prices['marketId'] = str(m.get('id', ''))
                    latest_prices['endDate'] = m.get('endDate', '')
                    latest_prices['conditionId'] = m.get('conditionId', '')
                    latest_prices['updatedAt'] = time.time()
                    break
        except Exception as e:
            print(f'fetch_prices error: {e}')
        time.sleep(1)

threading.Thread(target=fetch_prices, daemon=True).start()

@app.route('/')
def health():
    return jsonify({'status': 'ok'})

@app.route('/prices')
def prices():
    return jsonify(latest_prices)

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
