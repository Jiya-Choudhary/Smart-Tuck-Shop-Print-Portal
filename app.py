from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
import sqlite3
import os
import time

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
            status TEXT,
            task_type TEXT DEFAULT 'Print Out',
            file_path TEXT
        )
    """)
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN copies INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN task_type TEXT DEFAULT 'Print Out'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN file_path TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

create_table()


def parse_token_num(token_val):
    if token_val is None:
        return 0
    if isinstance(token_val, int):
        return token_val
    digits = ''.join(c for c in str(token_val) if c.isdigit())
    return int(digits) if digits else 0


def update_pending_tokens(conn):
    cursor = conn.cursor()
    
    # Fetch all Pending orders
    cursor.execute("SELECT * FROM orders WHERE status = 'Pending' ORDER BY id ASC")
    pending_orders = cursor.fetchall()
    
    if not pending_orders:
        return
        
    # Get all active/completed order tokens to find start_token
    token_nums = [parse_token_num(o['token']) for o in pending_orders if o['token'] is not None]
    if token_nums:
        start_token = min(token_nums)
    else:
        cursor.execute("SELECT token FROM orders WHERE status != 'Pending'")
        rows = cursor.fetchall()
        other_tokens = [parse_token_num(r[0]) for r in rows if r[0] is not None]
        start_token = max(other_tokens) + 1 if other_tokens else 1
        
    import datetime
    
    def get_priority_group(payment, pickup_time_str):
        try:
            pickup_h, pickup_m = map(int, pickup_time_str.split(':'))
            now = datetime.datetime.now()
            current_minutes = now.hour * 60 + now.minute
            pickup_minutes = pickup_h * 60 + pickup_m
            
            # Early pickup: scheduled within 2 hours (120 mins) from now (including past slots)
            is_early = (pickup_minutes - current_minutes) <= 120
        except Exception:
            is_early = False
            
        if payment == 'UPI Online':
            return 1 if is_early else 3
        else: # 'Pay on Pickup'
            return 2 if is_early else 4

    orders_list = []
    for o in pending_orders:
        od = dict(o)
        group = get_priority_group(od['payment'], od['pickup_time'])
        orders_list.append((group, od['pickup_time'], od['id'], od))
        
    # Sort: group (1-4) ASC, pickup_time ASC, id ASC
    orders_list.sort(key=lambda x: (x[0], x[1], x[2]))
    
    # Assign contiguous tokens (e.g. A0012, B0013)
    for i, (group, _, _, od) in enumerate(orders_list):
        char = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}[group]
        new_token_num = start_token + i
        new_token = f"{char}{new_token_num:04d}"
        cursor.execute("UPDATE orders SET token = ? WHERE id = ?", (new_token, od['id']))


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
    task_type = request.form.get("task_type", "Print Out")
    
    file_path = None
    if task_type == "Print Out" and "file" in request.files:
        file = request.files["file"]
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            unique_filename = f"{int(time.time())}_{filename}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_filename))
            file_path = unique_filename

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT token FROM orders")
    rows = cursor.fetchall()
    all_tokens = [parse_token_num(r[0]) for r in rows if r[0] is not None]
    max_token_num = max(all_tokens) if all_tokens else 0
    temp_token = f"T{max_token_num + 1:04d}"
        
    cursor.execute(
        "INSERT INTO orders (token, name, roll_no, pages, copies, print_type, pickup_time, payment, status, task_type, file_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (temp_token, name, roll_no, pages, copies, print_type, pickup_time, payment, 'Pending', task_type, file_path)
    )
    order_id = cursor.lastrowid
    
    update_pending_tokens(conn)
    
    conn.commit()
    conn.close()
    
    return redirect(f"/success/{order_id}")


@app.route("/success/<int:order_id>")
def success(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    conn.close()
    
    if not order:
        return redirect("/")
        
    return render_template("success.html", order=order)


@app.route("/cancel/<int:order_id>", methods=["POST"])
def cancel_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    
    if order:
        if order['payment'] == 'Pay on Pickup' and order['status'] == 'Pending':
            cursor.execute("UPDATE orders SET status = 'Cancelled' WHERE id = ?", (order_id,))
            update_pending_tokens(conn)
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
        update_pending_tokens(conn)
        conn.commit()
        conn.close()
    return redirect("/admin")


if __name__ == "__main__":
    app.run(debug=True)