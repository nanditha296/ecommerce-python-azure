from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, os
from azure.storage.queue import QueueClient   # NEW import

app = Flask(__name__)
app.secret_key = "secret-key-123"  # You can change this to any random string

# -------------------------------------------------------
# DATABASE CONNECTION
# -------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect("database/products.db")
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------------------------------------
# INITIALIZE DATABASE (Run Once)
# -------------------------------------------------------
def init_db():
    os.makedirs("database", exist_ok=True)
    conn = get_db_connection()
    # Products table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0
        )
    """)
    # Orders table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total REAL,
            payment_type TEXT,
            status TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# -------------------------------------------------------
# QUEUE SERVICE
# -------------------------------------------------------
def enqueue_order(order_id: int):
    queue_client = QueueClient.from_connection_string(
        conn_str=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        queue_name="orders-queue"
    )
    queue_client.send_message(str(order_id))
    print(f"Order {order_id} placed into queue")

# -------------------------------------------------------
# HOME PAGE – DISPLAY PRODUCTS
# -------------------------------------------------------
@app.route("/")
def index():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("index.html", products=products)

# -------------------------------------------------------
# ADD TO CART
# -------------------------------------------------------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()

    if not product:
        return redirect(url_for("index"))

    cart = session.get("cart", [])
    found = False

    for item in cart:
        if item["id"] == product["id"]:
            item["quantity"] += 1
            found = True
            break

    if not found:
        cart.append({
            "id": product["id"],
            "name": product["name"],
            "price": float(product["price"]),
            "quantity": 1
        })

    session["cart"] = cart
    session.modified = True
    return redirect(url_for("cart"))

# -------------------------------------------------------
# VIEW CART
# -------------------------------------------------------
@app.route("/cart")
def cart():
    cart = session.get("cart", [])
    total = sum(item["price"] * item["quantity"] for item in cart)
    return render_template("cart.html", cart=cart, total=total)

# -------------------------------------------------------
# UPDATE QUANTITY
# -------------------------------------------------------
@app.route("/update_quantity/<int:product_id>/<action>")
def update_quantity(product_id, action):
    cart = session.get("cart", [])
    for item in cart:
        if item["id"] == product_id:
            if action == "increase":
                item["quantity"] += 1
            elif action == "decrease" and item["quantity"] > 1:
                item["quantity"] -= 1
            break
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("cart"))

# -------------------------------------------------------
# REMOVE FROM CART
# -------------------------------------------------------
@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", [])
    cart = [item for item in cart if item["id"] != product_id]
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("cart"))

# -------------------------------------------------------
# CHECKOUT (UPDATED)
# -------------------------------------------------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        payment_type = request.form.get("payment_type")
        total = float(request.form.get("total", 0))
        cart = session.get("cart", [])

        # Save order in DB with status = Pending
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (total, payment_type, status) VALUES (?, ?, ?)",
                       (total, payment_type, "Pending"))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Enqueue order ID for async processing
        enqueue_order(order_id)

        # Clear cart
        session.pop("cart", None)

        return render_template("checkout.html", total=total, payment_type=payment_type, order_id=order_id)
    else:
