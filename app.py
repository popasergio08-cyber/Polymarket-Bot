import os, json, time, threading, requests
from flask import Flask, request, jsonify
from py_clob_client_v2 import ClobClient, OrderArgs
from py_clob_client_v2.clob_types import ApiCreds
from py_clob_client_v2.order_builder.constants import BUY

app = Flask(__name__)

PRIVATE_KEY = os.getenv('PRIVATE_KEY')
POLY_KEY = os.getenv('API_KEY')
POLY_SECRET = os.getenv('SECRET')
PASSPHRASE = os.getenv('PASSPHRASE')
WALLET = os.getenv('WALLET_ADDRESS')

client = ClobClient(
    host='https://clob.polymarket.com',
    chain_id=137,
    key=PRIVATE_KEY,
    creds=ApiCreds(
        [REDACTED]
        api_secret=POLY_SECRET,
        api_passphrase=PASSPHRASE
    ),
    signature_type=1,
    funder=WALLET
)

def get_prices():
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
                return {
                    'upPrice': float(prices[up_idx]),
                    'downPrice': float(prices[dn_idx]),
                    'upTokenId': tokens[up_idx],
                    'downTokenId': tokens[dn_idx],
                    'marketSlug': m.get('slug', ''),
                    'marketId': str(m.get('id', '')),
                    'endDate': m.get('endDate', ''),
                    'conditionId': m.get('conditionId', '')
                }
    except Exception as e:
        print(f'get_prices error: {e}')
    return None
@app.route('/')
def health():
    return jsonify({'status': 'ok'})

@app.route('/check', methods=['POST'])
def check():
    """
    Controlla il prezzo ogni secondo per 55 secondi.
    Se trova UP o DOWN nella soglia, risponde subito con i dati.
    Altrimenti dopo 55 secondi risponde con hasSignal: false.
    Il body deve contenere: minPrice, maxPrice, state (free/waitingSecond/completed), firstBought
    """
    body = request.get_json(force=True) or {}
    min_price = float(body.get('minPrice', 0.56))
    max_price = float(body.get('maxPrice', 0.64))
    state = body.get('state', 'free')
    first_bought = body.get('firstBought', None)

    deadline = time.time() + 55

    while time.time() < deadline:
        d = get_prices()
        if d:
            up = d['upPrice']
            dn = d['downPrice']

            if state == 'free':
                if min_price <= up <= max_price:
                    return jsonify({**d, 'hasSignal': True, 'side': 'UP',
                                    'amount': 5, 'tokenId': d['upTokenId'],
                                    'price': up, 'reason': f'UP a {int(up*100)}¢ acquisto 5euro'})
                if min_price <= dn <= max_price:
                    return jsonify({**d, 'hasSignal': True, 'side': 'DOWN',
                                    'amount': 5, 'tokenId': d['downTokenId'],
                                    'price': dn, 'reason': f'DOWN a {int(dn*100)}¢ acquisto 5euro'})

            elif state == 'waitingSecond':
                if first_bought == 'up':
                    if dn >= 0.34:
                        return jsonify({**d, 'hasSignal': True, 'side': 'DOWN',
                                        'amount': 2.5, 'tokenId': d['downTokenId'],
                                        'price': dn, 'reason': f'DOWN a {int(dn*100)}¢ STOP 2.5euro'})
                    if up < min_price and dn >= 0.50:
                        return jsonify({**d, 'hasSignal': True, 'side': 'DOWN',
                                        'amount': 5, 'tokenId': d['downTokenId'],
                                        'price': dn, 'reason': f'UP scesa, DOWN a {int(dn*100)}¢ riparte 5euro'})
                elif first_bought == 'down':
                    if up >= 0.34:
                        return jsonify({**d, 'hasSignal': True, 'side': 'UP',
                                        'amount': 2.5, 'tokenId': d['upTokenId'],
                                        'price': up, 'reason': f'UP a {int(up*100)}¢ STOP 2.5euro'})
                    if dn < min_price and up >= 0.50:
                        return jsonify({**d, 'hasSignal': True, 'side': 
                                        'UP',
                                        'amount': 5, 'tokenId': d['upTokenId'],
                                        'price': up, 'reason': f'DOWN scesa, UP a {int(up*100)}¢ riparte 5euro'})

        time.sleep(1)

    # Nessun segnale in 55 secondi
    last = get_prices() or {}
    return jsonify({**last, 'hasSignal': False})

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
