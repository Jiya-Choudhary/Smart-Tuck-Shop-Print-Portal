from flask import Flask, render_template, request, redirect
import sqlite3
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token INTEGER,
            name TEXT,
            roll_no TEXT,
            pages INTEGER,
            copies INTEGER DEFAULT 1,
            print_type TEXT,
            pickup_time TEXT,
            payment TEXT,
            status TEXT
        )
    """)
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN copies INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

create_table()


@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Pending', 'Processing')")
    active_count = cursor.fetchone()[0]
    
    roll_no = request.args.get('roll_no')
    orders = []
    if roll_no:
        cursor.execute("SELECT * FROM orders WHERE roll_no = ? ORDER BY id DESC", (roll_no,))
        orders = cursor.fetchall()
    
    conn.close()
    return render_template("home.html", active_count=active_count, orders=orders, searched_roll_no=roll_no)


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form["name"]
    roll_no = request.form["roll_no"]
    pages = int(request.form["pages"])
    copies = int(request.form.get("copies", 1))
    print_type = request.form["print_type"]
    pickup_time = request.form["pickup_time"]
    payment = request.form["payment"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if payment == 'UPI Online':
        cursor.execute("SELECT MIN(token) FROM orders WHERE payment = 'Pay on Pickup' AND status = 'Pending'")
        row = cursor.fetchone()
        first_unpaid_token = row[0] if row and row[0] is not None else None
        
        if first_unpaid_token is not None:
            new_token = first_unpaid_token
            cursor.execute("UPDATE orders SET token = token + 1 WHERE payment = 'Pay on Pickup' AND status = 'Pending' AND token >= ?", (first_unpaid_token,))
        else:
            cursor.execute("SELECT MAX(token) FROM orders")
            row_max = cursor.fetchone()
            max_token = row_max[0] if row_max and row_max[0] is not None else 0
            new_token = max_token + 1
    else:
        cursor.execute("SELECT MAX(token) FROM orders")
        row_max = cursor.fetchone()
        max_token = row_max[0] if row_max and row_max[0] is not None else 0
        new_token = max_token + 1
        
    cursor.execute(
        "INSERT INTO orders (token, name, roll_no, pages, copies, print_type, pickup_time, payment, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (new_token, name, roll_no, pages, copies, print_type, pickup_time, payment, 'Pending')
    )
    conn.commit()
    conn.close()
    
    return redirect(f"/?roll_no={roll_no}&success=true")


@app.route("/cancel/<int:order_id>", methods=["POST"])
def cancel_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    
    if order:
        if order['payment'] == 'Pay on Pickup' and order['status'] == 'Pending':
            cursor.execute("UPDATE orders SET status = 'Cancelled' WHERE id = ?", (order_id,))
            cursor.execute("UPDATE orders SET token = token - 1 WHERE payment = 'Pay on Pickup' AND status = 'Pending' AND token > ?", (order['token'],))
            conn.commit()
            
    conn.close()
    roll_no = order['roll_no'] if order else ''
    return redirect(f"/?roll_no={roll_no}")


@app.route("/admin")
def admin():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY CASE WHEN status = 'Processing' THEN 1 WHEN status = 'Pending' THEN 2 WHEN status = 'Completed' THEN 3 ELSE 4 END, token ASC, id ASC")
    orders = cursor.fetchall()
    conn.close()
    return render_template("admin.html", orders=orders)


@app.route("/admin/update/<int:order_id>", methods=["POST"])
def admin_update(order_id):
    status = request.form.get("status")
    if status in ['Pending', 'Processing', 'Completed', 'Cancelled']:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        conn.commit()
        conn.close()
    return redirect("/admin")


if __name__ == "__main__":
    app.run(debug=True)