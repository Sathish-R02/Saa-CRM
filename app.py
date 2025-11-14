from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB = "crm.db"


# ---------------------------------------------------------
# Utility: Create Tables if Not Exists
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


# Initialize DB
init_db()


# ---------------------------------------------------------
#   CUSTOMER CRUD
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
#   PRODUCT + STOCK
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
#   SIMPLE BILLING (INR) + SALES
# ---------------------------------------------------------
@app.route("/billing", methods=["POST"])
def create_bill():
    """
    Body format:
    {
      "customer_id": 1,
      "items": [
        {"product_id": 2, "qty": 3},
        {"product_id": 5, "qty": 1}
      ]
    }
    """
    data = request.json
    customer_id = data["customer_id"]
    items = data["items"]

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Calculate total
    total_amount = 0

    for item in items:
        product_id = item["product_id"]
        qty = item["qty"]

        cur.execute("SELECT price, stock FROM products WHERE id=?", (product_id,))
        product = cur.fetchone()

        if not product:
            return jsonify({"error": "Product not found"}), 404

        price, stock = product

        if qty > stock:
            return jsonify({"error": "Insufficient stock"}), 400

        total_amount += price * qty

        # Update stock
        cur.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (qty, product_id)
        )

    # Create sale
    sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO sales (customer_id, total, date) VALUES (?, ?, ?)",
        (customer_id, total_amount, sale_date)
    )
    sale_id = cur.lastrowid

    # Insert sale items
    for item in items:
        product_id = item["product_id"]
        qty = item["qty"]

        cur.execute("SELECT price FROM products WHERE id=?", (product_id,))
        price = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO sale_items (sale_id, product_id, qty, price) VALUES (?, ?, ?, ?)",
            (sale_id, product_id, qty, price)
        )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Bill created",
        "sale_id": sale_id,
        "total_in_inr": f"₹ {total_amount:.2f}"
    })


# ---------------------------------------------------------
# Dashboard: Sales List
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


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
