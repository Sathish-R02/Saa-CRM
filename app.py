from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Use absolute path (important for Render!)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crm.db")


# ---------------------------------------------------------
# Create Tables
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            address TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            stock INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            total REAL,
            date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            product_id INTEGER,
            qty INTEGER,
            price REAL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------------------------------------------------
# CUSTOMER CRUD
# ---------------------------------------------------------
@app.route("/customers", methods=["POST"])
def add_customer():
    data = request.json
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)",
        (data["name"], data["phone"], data["address"])
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Customer added"}), 201


@app.route("/customers", methods=["GET"])
def list_customers():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers")
    rows = cur.fetchall()
    conn.close()

    customers = [
        {"id": r[0], "name": r[1], "phone": r[2], "address": r[3]}
        for r in rows
    ]
    return jsonify(customers)


# ---------------------------------------------------------
# PRODUCT CRUD
# ---------------------------------------------------------
@app.route("/products", methods=["POST"])
def add_product():
    data = request.json
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
        (data["name"], data["price"], data["stock"])
    )

    conn.commit()
    conn.close()
    return jsonify({"message": "Product added"}), 201


@app.route("/products", methods=["GET"])
def list_products():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    rows = cur.fetchall()
    conn.close()

    products = [
        {"id": r[0], "name": r[1], "price": r[2], "stock": r[3]}
        for r in rows
    ]
    return jsonify(products)


# ---------------------------------------------------------
# SIMPLE BILLING (INR)
# ---------------------------------------------------------
@app.route("/billing", methods=["POST"])
def create_bill():
    data = request.json
    customer_id = data["customer_id"]
    items = data["items"]

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    total_amount = 0

    for item in items:
        cur.execute("SELECT price, stock FROM products WHERE id=?", (item["product_id"],))
        product = cur.fetchone()

        if not product:
            return jsonify({"error": "Product not found"}), 404

        price, stock = product

        if item["qty"] > stock:
            return jsonify({"error": "Not enough stock"}), 400

        total_amount += price * item["qty"]

        # Update stock
        cur.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (item["qty"], item["product_id"])
        )

    sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO sales (customer_id, total, date) VALUES (?, ?, ?)",
        (customer_id, total_amount, sale_date)
    )
    sale_id = cur.lastrowid

    # Sale items
    for item in items:
        cur.execute("SELECT price FROM products WHERE id=?", (item["product_id"],))
        price = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO sale_items (sale_id, product_id, qty, price) VALUES (?, ?, ?, ?)",
            (sale_id, item["product_id"], item["qty"], price)
        )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Bill created",
        "sale_id": sale_id,
        "total": f"₹ {total_amount:.2f}"
    })


# ---------------------------------------------------------
# SALES LIST
# ---------------------------------------------------------
@app.route("/sales", methods=["GET"])
def list_sales():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM sales ORDER BY date DESC")
    rows = cur.fetchall()
    conn.close()

    sales = [
        {"id": r[0], "customer_id": r[1], "total": f"₹ {r[2]:.2f}", "date": r[3]}
        for r in rows
    ]
    return jsonify(sales)


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "CRM backend running"})


# ---------------------------------------------------------
# RUN (Gunicorn on Render)
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
