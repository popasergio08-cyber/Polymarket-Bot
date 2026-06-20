from flask import Flask, request, jsonify
import threading
import time
import requests
import os
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType, BalanceAllowanceParams, AssetType

app = Flask(__name__)

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
POLY_KEY = os.environ.get("POLY_KEY")
POLY_SECRET = os.environ.get("POLY_SECRET")
PASSPHRASE = os.environ.get("PASSPHRASE")
WALLET_ADDRESS = os.environ.get("WALLET_ADDRESS")

def get_client():
    creds = ApiCreds(
        [REDACTED]
        api_secret=POLY_SECRET,
        api_passphrase=PASSPHRASE
    )
    client = ClobClient(
        HOST,
        key=PRIVATE_KEY,
        chain_id=CHAIN_ID,
        creds=creds,
        signature_type=1,
        funder=WALLET_ADDRESS
    )
    return client
def fetch_btc_market():
    now = int(time.time())
    block = (now // 900) * 900
    slug = f"btc-updown-15m-{block}"
    try:
        url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if not data:
            return None
        m = data[0]
        tokens = m.get("tokens", [])
        up_token = next((t for t in tokens if t.get("outcome","").upper() == "UP"), None)
        down_token = next((t for t in tokens if t.get("outcome","").upper() == "DOWN"), None)
        if not up_token or not down_token:
            return None
        return {
            "marketId": str(m.get("id","")),
            "marketSlug": slug,
            "conditionId": m.get("conditionId",""),
            "endDate": m.get("endDateIso") or m.get("endDate",""),
            "upPrice": float(up_token.get("price", 0)),
            "downPrice": float(down_token.get("price", 0)),
            "upTokenId": up_token.get("token_id",""),
            "downTokenId": down_token.get("token_id","")
        }
    except Exception as e:
        return None
        @app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok"})

@app.route("/prices", methods=["GET"])
def prices():
    m = fetch_btc_market()
    if not m:
        return jsonify({"error": "market not found"}), 404
    return jsonify(m)

@app.route("/check", methods=["POST"])
def check():
    body = request.get_json(force=True) or {}
    status = body.get("status", "free")
    first_bought = body.get("firstBought", None)
    last_market_id = body.get("lastMarketId", "")
    notified_market_id = body.get("notifiedMarketId", "")
    min_price = float(body.get("minPrice", 0.56))
    max_price = float(body.get("maxPrice", 0.64))
    stop_price = float(body.get("stopPrice", 0.34))
    restart_price = float(body.get("restartPrice", 0.50))
    first_amount = float(body.get("firstAmount", 5))
    stop_amount = float(body.get("stopAmount", 2.5))
    restart_amount = float(body.get("restartAmount", 5))
deadline = time.time() + 55

    while time.time() < deadline:
        m = fetch_btc_market()
        if not m:
            time.sleep(1)
            continue

        market_id = m["marketId"]
        up_price = m["upPrice"]
        down_price = m["downPrice"]

        is_new_market = (market_id != last_market_id)
        if is_new_market:
            status = "free"
            first_bought = None
            last_market_id = market_id

        should_notify = is_new_market and (market_id != notified_market_id)
        if should_notify:
            notified_market_id = market_id
            new_state = {
                "status": status,
                "firstBought": first_bought,
                "lastMarketId": last_market_id,
                "notifiedMarketId": notified_market_id
            }
            return jsonify({
                "action": "newMarket",
                "isNewMarket": True,
                "upPrice": up_price,
                "downPrice": down_price,
                "marketId": market_id,
                "marketSlug": m["marketSlug"],
                "conditionId": m["conditionId"],
                "endDate": m["endDate"],
                "newState": new_state
            })
    if status == "completed":
            time.sleep(1)
            continue

        order = None

        if status == "free":
            if min_price <= up_price <= max_price:
                order = {
                    "side": "UP",
                    "tokenId": m["upTokenId"],
                    "price": up_price,
                    "amount": first_amount,
                    "reason": f"UP a {int(up_price*100)}c acquisto {first_amount}euro"
                }
                status = "waitingSecond"
                first_bought = "up"
            elif min_price <= down_price <= max_price:
                order = {
                    "side": "DOWN",
                    "tokenId": m["downTokenId"],
                    "price": down_price,
                    "amount": first_amount,
                    "reason": f"DOWN a {int(down_price*100)}c acquisto {first_amount}euro"
                }
                status = "waitingSecond"
                first_bought = "down"

        elif status == "waitingSecond":
            if first_bought == "up":
                if down_price >= stop_price:
                    order = {
                        "side": "DOWN",
                        "tokenId": m["downTokenId"],
                        "price": down_price,
                        "amount": stop_amount,
                        "reason": f"DOWN a {int(down_price*100)}c STOP {stop_amount}euro"
                    }
                    status = "completed"
                    first_bought = None
                elif up_price < min_price and down_price >= restart_price:
                    order = {
                        "side": "DOWN",
                    "tokenId": m["downTokenId"],
                        "price": down_price,
                        "amount": restart_amount,
                        "reason": f"UP scesa, DOWN a {int(down_price*100)}c riparte {restart_amount}euro"
                    }
                    status = "free"
                    first_bought = None
            elif first_bought == "down":
                if up_price >= stop_price:
                    order = {
                        "side": "UP",
                        "tokenId": m["upTokenId"],
                        "price": up_price,
                        "amount": stop_amount,
                        "reason": f"UP a {int(up_price*100)}c STOP {stop_amount}euro"
                    }
                    status = "completed"
                    first_bought = None
                elif down_price < min_price and up_price >= restart_price:
                    order = {
                        "side": "UP",
                        "tokenId": m["upTokenId"],
                        "price": up_price,
                        "amount": restart_amount,
                        "reason": f"DOWN scesa, UP a {int(up_price*100)}c riparte {restart_amount}euro"
                    }
                    status = "free"
                    first_bought = None

        if order:
            new_state = {
                "status": status,
                "firstBought": first_bought,
                "lastMarketId": last_market_id,
                "notifiedMarketId": notified_market_id
            }
            return jsonify({
                "action": "order",
                "isNewMarket": False,
                **order,
                "upPrice": up_price,
                "downPrice": down_price,
                "marketId": market_id,
                "marketSlug": m["marketSlug"],
                "conditionId": m["conditionId"],
                "endDate": m["endDate"],
                "newState": new_state
            })
    time.sleep(1)

    return jsonify({"action": "none", "isNewMarket": False})

@app.route("/order", methods=["POST"])
def place_order():
    try:
        body = request.get_json(force=True) or {}
        token_id = body.get("tokenId")
        price = float(body.get("price", 0))
        amount = float(body.get("amount", 0))

        client = get_client()
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=amount,
            side="BUY",
            order_type=OrderType.GTC
        )
        resp = client.create_and_post_order(order_args)
        order_id = resp.get("orderID") or resp.get("id") or resp.get("order_id","")
        return jsonify({"success": True, "orderID": order_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
