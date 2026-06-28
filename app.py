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

            print_type TEXT,

            pickup_time TEXT,

            payment TEXT,

            status TEXT

        )
    """)

    conn.commit()

    conn.close()


create_table()


@app.route('/')
def home():

    return render_template("home.html")


if __name__ == "__main__":
    app.run(debug=True)

@app.route("/submit", methods=["POST"])
def submit():

    name = request.form["name"]
    roll_no = request.form["roll_no"]
    pages = request.form["pages"]
    print_type = request.form["print_type"]
    pickup_time = request.form["pickup_time"]
    payment = request.form["payment"]

    return f"Order received from {name}"