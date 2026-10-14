#!/usr/bin/env python3
"""Flask web entry point for Smart Inventory & Order Management System."""
import os
from flask import Flask, jsonify, render_template, request
from database import db

app = Flask(__name__)

@app.get("/")
@app.get("/index.html")
def index():
    return render_template("index.html")

@app.get("/api/state")
def api_state():
    return jsonify(db.get_all_state())

@app.post("/api/products")
def api_add_product():
    payload = request.get_json(silent=True) or {}
    success, msg = db.add_product(payload)
    return jsonify({"success": success, "message": msg})

@app.post("/api/products/update")
def api_update_product():
    payload = request.get_json(silent=True) or {}
    success, msg = db.update_product(payload)
    return jsonify({"success": success, "message": msg})

@app.post("/api/restock")
def api_restock():
    payload = request.get_json(silent=True) or {}
    try:
        qty = int(payload.get("qty", 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Quantity must be a number"}), 400
    success, msg = db.restock_product(payload.get("itemId"), qty, payload.get("note", ""))
    return jsonify({"success": success, "message": msg})

@app.post("/api/checkout")
def api_checkout():
    payload = request.get_json(silent=True) or {}
    customer = payload.get("customer", "Student")
    cart = payload.get("cart", [])
    subtotal = payload.get("subtotal", 0)
    discount = payload.get("discount", 0)
    tax = payload.get("tax", 0)
    total = payload.get("total", 0)
    success, inv_id = db.checkout(customer, cart, subtotal, discount, tax, total)
    return jsonify({"success": success, "invoiceId": inv_id})

@app.post("/api/demo")
def api_demo():
    db.load_demo_data()
    return jsonify({"success": True, "message": "Demo data loaded"})

@app.post("/api/db-config")
def api_db_config():
    payload = request.get_json(silent=True) or {}
    db.save_config(payload.get("use_postgres"), payload.get("pg_url", ""))
    return jsonify({"success": True, "message": db.connection_msg})

@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "API endpoint not found"}), 404
    return "Page not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print("\n" + "=" * 60)
    print("  SMART INVENTORY & ORDER MANAGEMENT SYSTEM")
    print("  Designed & Deployed by: Amit Prajapat")
    print(f"  Local Web Link: http://127.0.0.1:{port}")
    print("  Database: PostgreSQL with SQLite fallback")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)
