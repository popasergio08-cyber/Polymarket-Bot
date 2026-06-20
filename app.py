from flask import Flask, jsonify, request
import os, time, requests

app = Flask(__name__)

PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
POLY_KEY = os.environ.get("POLY_KEY")
POLY_SECRET = os.environ.get("POLY_SECRET")
PASSPHRASE = os.environ.get("PASSPHRASE")
WALLET_ADDRESS = os.environ.get("WALLET_ADDRESS")

@app.route("/")
def home():
    return jsonify({"status": "ok"})

@app.route("/check", methods=["POST"])
def check():
    return jsonify({"action": "none", "isNewMarket": False})

@app.route("/order", methods=["POST"])
def order():
    return jsonify({"success": False, "error": "not implemented"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
