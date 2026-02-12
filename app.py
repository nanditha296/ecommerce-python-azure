from queue_service import enqueue_order

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        payment_type = request.form.get("payment_type")
        total = float(request.form.get("total", 0))
        cart = session.get("cart", [])

        # Save order in DB with status = Pending
        conn = get_db_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total REAL,
                payment_type TEXT,
                status TEXT
            )
        """)
        conn.commit()

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
        cart = session.get("cart", [])
        total = sum(item["price"] * item["quantity"] for item in cart)
        return render_template("checkout.html", total=total, payment_type=None)
