from flask import Flask, render_template, request, redirect, send_from_directory, session, url_for
from werkzeug.utils import secure_filename
import sqlite3
import os
import time

app = Flask(__name__)
app.secret_key = "smart_tuck_shop_print_portal_secret_key"

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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('shop_status', 'open')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('shop_announcement', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rate_print_bw', '2.00')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rate_print_color', '5.00')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rate_photo_bw', '2.00')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rate_photo_color', '5.00')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_username', 'admin')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password', 'admin123')")
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
    
    cursor.execute("SELECT * FROM orders WHERE status = 'Pending' ORDER BY id ASC")
    pending_orders = cursor.fetchall()
    
    if not pending_orders:
        return
        
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
            
            is_early = (pickup_minutes - current_minutes) <= 120
        except Exception:
            is_early = False
            
        if payment == 'UPI Online':
            return 1 if is_early else 3
        else:
            return 2 if is_early else 4

    orders_list = []
    for o in pending_orders:
        od = dict(o)
        group = get_priority_group(od['payment'], od['pickup_time'])
        orders_list.append((group, od['pickup_time'], od['id'], od))
        
    orders_list.sort(key=lambda x: (x[0], x[1], x[2]))
    
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
    
    cursor.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    
    roll_no = request.args.get('roll_no')
    orders = []
    if roll_no:
        cursor.execute("SELECT * FROM orders WHERE roll_no = ? ORDER BY id DESC", (roll_no,))
        orders = cursor.fetchall()
    
    conn.close()
    return render_template("home.html", active_count=active_count, orders=orders, searched_roll_no=roll_no, shop_status=settings.get('shop_status', 'open'), shop_announcement=settings.get('shop_announcement', ''), settings=settings)

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
    
    cursor.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    
    if not order:
        return redirect("/")
        
    return render_template("success.html", order=order, settings=settings)

@app.route("/cancel/<int:order_id>", methods=["POST"])
def cancel_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    
    if order:
        if order['payment'] and order['payment'].startswith('Pay on Pickup') and order['status'] == 'Pending':
            cursor.execute("UPDATE orders SET status = 'Cancelled' WHERE id = ?", (order_id,))
            update_pending_tokens(conn)
            conn.commit()
            
    conn.close()
    roll_no = order['roll_no'] if order else ''
    return redirect(f"/?roll_no={roll_no}")

@app.before_request
def require_login():
    if request.path.startswith("/admin") and request.path != "/admin/login":
        if not session.get("logged_in"):
            return redirect(url_for("admin_login"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("logged_in"):
        return redirect(url_for("admin"))
    
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'admin_username'")
        db_user = cursor.fetchone()
        cursor.execute("SELECT value FROM settings WHERE key = 'admin_password'")
        db_pass = cursor.fetchone()
        conn.close()
        
        expected_user = db_user['value'] if db_user else 'admin'
        expected_pass = db_pass['value'] if db_pass else 'admin123'
        
        if username == expected_user and password == expected_pass:
            session["logged_in"] = True
            return redirect(url_for("admin"))
        else:
            error = "Invalid username or password."
            
    return render_template("login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("logged_in", None)
    return redirect(url_for("admin_login"))

@app.route("/admin/change-password", methods=["POST"])
def admin_change_password():
    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'admin_password'")
    row = cursor.fetchone()
    db_pass = row['value'] if row else 'admin123'
    
    if current_password != db_pass:
        conn.close()
        session["password_error"] = "Incorrect current password."
        return redirect(url_for("admin"))
        
    if new_password != confirm_password:
        conn.close()
        session["password_error"] = "New passwords do not match."
        return redirect(url_for("admin"))
        
    if not new_password:
        conn.close()
        session["password_error"] = "New password cannot be empty."
        return redirect(url_for("admin"))
        
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password', ?)", (new_password,))
    conn.commit()
    conn.close()
    session["password_success"] = "Password updated successfully!"
    return redirect(url_for("admin"))

@app.route("/admin")
def admin():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY CASE WHEN status = 'Processing' THEN 1 WHEN status = 'Pending' THEN 2 WHEN status = 'Completed' THEN 3 ELSE 4 END, token ASC, id ASC")
    orders = cursor.fetchall()
    
    cursor.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    
    pwd_error = session.pop("password_error", None)
    pwd_success = session.pop("password_success", None)
    
    return render_template("admin.html", orders=orders, shop_status=settings.get('shop_status', 'open'), shop_announcement=settings.get('shop_announcement', ''), settings=settings, pwd_error=pwd_error, pwd_success=pwd_success)

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

@app.route("/admin/toggle-shop", methods=["POST"])
def admin_toggle_shop():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'shop_status'")
    row = cursor.fetchone()
    current = row[0] if row else 'open'
    new_status = 'closed' if current == 'open' else 'open'
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('shop_status', ?)", (new_status,))
    conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/admin/toggle-payment/<int:order_id>", methods=["POST"])
def admin_toggle_payment(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT payment FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    if row:
        current = row['payment']
        method = request.form.get("method")
        if current in ['Pay on Pickup', 'Pay on Pickup (Cash)', 'Pay on Pickup (UPI)']:
            if method == 'UPI':
                new_val = 'Pay on Pickup (UPI Paid)'
            else:
                new_val = 'Pay on Pickup (Cash Paid)'
        elif current in ['Pay on Pickup (UPI Paid)', 'Pay on Pickup (Cash Paid)', 'Pay on Pickup (UPI) (Paid)', 'Pay on Pickup (Cash) (Paid)', 'Pay on Pickup (Paid)']:
            new_val = 'Pay on Pickup'
        else:
            new_val = current
        cursor.execute("UPDATE orders SET payment = ? WHERE id = ?", (new_val, order_id))
        conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/admin/update-announcement", methods=["POST"])
def admin_update_announcement():
    announcement = request.form.get("shop_announcement", "").strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('shop_announcement', ?)", (announcement,))
    conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/admin/update-rates", methods=["POST"])
def admin_update_rates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('rate_print_bw', ?)", (request.form.get('rate_print_bw'),))
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('rate_print_color', ?)", (request.form.get('rate_print_color'),))
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('rate_photo_bw', ?)", (request.form.get('rate_photo_bw'),))
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('rate_photo_color', ?)", (request.form.get('rate_photo_color'),))
    conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/admin/bulk-update", methods=["POST"])
def admin_bulk_update():
    status = request.form.get("status")
    order_ids = request.form.getlist("order_ids")
    if status in ['Pending', 'Processing', 'Completed', 'Cancelled'] and order_ids:
        conn = get_db_connection()
        cursor = conn.cursor()
        ids = [int(x) for x in order_ids if x.isdigit()]
        if ids:
            placeholders = ','.join('?' for _ in ids)
            cursor.execute(f"UPDATE orders SET status = ? WHERE id IN ({placeholders})", [status] + ids)
            update_pending_tokens(conn)
            conn.commit()
        conn.close()
    return redirect("/admin")

@app.route("/admin/export-csv")
def admin_export_csv():
    import csv
    from io import StringIO
    from flask import make_response
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    
    cursor.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    
    rate_print_bw = float(settings.get('rate_print_bw', 2.00))
    rate_print_color = float(settings.get('rate_print_color', 5.00))
    rate_photo_bw = float(settings.get('rate_photo_bw', 2.00))
    rate_photo_color = float(settings.get('rate_photo_color', 5.00))
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Token', 'Name', 'Roll No', 'Task Type', 'Print Type', 'Pages', 'Copies', 'Total Price (INR)', 'Pickup Time', 'Payment', 'Status', 'File Name'])
    
    for o in orders:
        is_print = o['task_type'] == 'Print Out'
        rate = rate_print_color if o['print_type'] == 'Color' and is_print else (rate_photo_color if o['print_type'] == 'Color' else (rate_print_bw if is_print else rate_photo_bw))
        total_price = o['pages'] * (o['copies'] or 1) * rate
        file_name = o['file_path'].split('_', 1)[1] if o['file_path'] and '_' in o['file_path'] else (o['file_path'] or '-')
        cw.writerow([
            o['id'],
            o['token'],
            o['name'],
            o['roll_no'],
            o['task_type'],
            o['print_type'],
            o['pages'],
            o['copies'] or 1,
            total_price,
            o['pickup_time'],
            o['payment'],
            o['status'],
            file_name
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=tuckshop_orders_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route("/admin/orders-api")
def admin_orders_api():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM orders")
    rows = cursor.fetchall()
    conn.close()
    
    max_id = max([r['id'] for r in rows]) if rows else 0
    status_str = "|".join(f"{r['id']}:{r['status']}" for r in rows)
    import hashlib
    status_hash = hashlib.md5(status_str.encode('utf-8')).hexdigest() if rows else ""
    
    return {
        "max_id": max_id,
        "status_hash": status_hash
    }

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == "__main__":
    app.run(debug=True)