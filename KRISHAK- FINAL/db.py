"""
db.py  --  a tiny SQLite database (the app's memory)
====================================================

We use Python's built-in `sqlite3`, so there is nothing extra to install and
the data is saved in a single file `kisansetu.db`. Four simple tables:

  farmers   -> who is selling (name, UPI id, village, wallet balance)
  listings  -> what is for sale (crop, grade, kg, price/kg)
  orders    -> what a buyer ordered (qty, amount, status)
  payments  -> the (simulated) UPI payments and where the money "went"
"""

import os
import sqlite3
from datetime import datetime

import pricing
import payments

DB_FILE = os.path.join(os.path.dirname(__file__), "kisansetu.db")


def conn():
    c = sqlite3.connect(DB_FILE)
    c.row_factory = sqlite3.Row          # rows behave like dictionaries
    return c


def init(seed=True):
    """Create tables if they don't exist, and add demo data the first time."""
    with conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS farmers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, vpa TEXT, village TEXT, wallet REAL DEFAULT 0);

            CREATE TABLE IF NOT EXISTS listings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_id INTEGER, crop TEXT, grade TEXT,
                qty_kg REAL, price_per_kg REAL, created TEXT);

            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER, buyer_name TEXT, qty_kg REAL,
                amount REAL, status TEXT, created TEXT);

            CREATE TABLE IF NOT EXISTS payments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER, txn_ref TEXT, method TEXT,
                amount REAL, farmer_payout REAL, status TEXT, created TEXT);

            CREATE TABLE IF NOT EXISTS donations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor TEXT, amount REAL, txn_ref TEXT, note TEXT, created TEXT);

            CREATE TABLE IF NOT EXISTS feedback(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_id INTEGER, farmer_name TEXT, farmer_type TEXT,
                ease INTEGER, price_fair TEXT, paid_fast TEXT,
                wants TEXT, comment TEXT, created TEXT);
            """
        )
    if seed:
        with conn() as c:
            n = c.execute("SELECT COUNT(*) FROM farmers").fetchone()[0]
        if n == 0:
            _seed()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _seed():
    """Add a few demo farmers and produce listings so the app isn't empty."""
    demo = [
        ("Ramesh Patil", "Nashik", [("Onion", "A", 500), ("Tomato", "B", 200)]),
        ("Sita Devi",    "Kolar",  [("Tomato", "A", 300), ("Banana", "A", 150)]),
        ("Lakshmi Rao",  "Guntur", [("Rice", "A", 800), ("Potato", "C", 400)]),
    ]
    for name, village, crops in demo:
        fid = add_farmer(name, village)
        for crop, grade, qty in crops:
            add_listing(fid, crop, grade, qty, pricing.suggested_price(crop, grade))


# ---------- farmers ----------
def add_farmer(name, village):
    with conn() as c:
        cur = c.execute(
            "INSERT INTO farmers(name, vpa, village, wallet) VALUES(?,?,?,0)",
            (name, payments.demo_vpa(name), village))
        return cur.lastrowid


def get_farmer(fid):
    with conn() as c:
        return c.execute("SELECT * FROM farmers WHERE id=?", (fid,)).fetchone()


def all_farmers():
    with conn() as c:
        return c.execute("SELECT * FROM farmers ORDER BY name").fetchall()


def credit_wallet(fid, amount):
    with conn() as c:
        c.execute("UPDATE farmers SET wallet = wallet + ? WHERE id=?", (amount, fid))


# ---------- listings ----------
def add_listing(farmer_id, crop, grade, qty_kg, price_per_kg):
    with conn() as c:
        cur = c.execute(
            "INSERT INTO listings(farmer_id,crop,grade,qty_kg,price_per_kg,created)"
            " VALUES(?,?,?,?,?,?)",
            (farmer_id, crop, grade, qty_kg, price_per_kg, _now()))
        return cur.lastrowid


def list_market():
    """All listings still in stock, joined with the farmer selling them."""
    with conn() as c:
        return c.execute(
            """SELECT l.*, f.name AS farmer, f.village, f.vpa
               FROM listings l JOIN farmers f ON f.id = l.farmer_id
               WHERE l.qty_kg > 0 ORDER BY l.created DESC""").fetchall()


def listings_by_farmer(fid):
    with conn() as c:
        return c.execute("SELECT * FROM listings WHERE farmer_id=? ORDER BY id DESC",
                         (fid,)).fetchall()


def reduce_stock(listing_id, qty):
    with conn() as c:
        c.execute("UPDATE listings SET qty_kg = qty_kg - ? WHERE id=?", (qty, listing_id))


def get_listing(listing_id):
    with conn() as c:
        return c.execute(
            """SELECT l.*, f.name AS farmer, f.id AS farmer_id, f.vpa
               FROM listings l JOIN farmers f ON f.id=l.farmer_id
               WHERE l.id=?""", (listing_id,)).fetchone()


# ---------- orders & payments ----------
def create_order(listing_id, buyer_name, qty_kg, amount):
    with conn() as c:
        cur = c.execute(
            "INSERT INTO orders(listing_id,buyer_name,qty_kg,amount,status,created)"
            " VALUES(?,?,?,?, 'PENDING', ?)",
            (listing_id, buyer_name, qty_kg, amount, _now()))
        return cur.lastrowid


def mark_order_paid(order_id):
    with conn() as c:
        c.execute("UPDATE orders SET status='PAID' WHERE id=?", (order_id,))


def record_payment(order_id, txn_ref, amount, farmer_payout):
    with conn() as c:
        c.execute(
            "INSERT INTO payments(order_id,txn_ref,method,amount,farmer_payout,status,created)"
            " VALUES(?,?, 'UPI (simulated)', ?,?, 'SUCCESS', ?)",
            (order_id, txn_ref, amount, farmer_payout, _now()))


def all_payments():
    with conn() as c:
        return c.execute(
            """SELECT p.*, o.buyer_name, o.qty_kg, l.crop, l.grade, f.name AS farmer
               FROM payments p
               JOIN orders o   ON o.id = p.order_id
               JOIN listings l ON l.id = o.listing_id
               JOIN farmers f  ON f.id = l.farmer_id
               ORDER BY p.id DESC""").fetchall()


def payments_for_farmer(fid):
    """All (simulated) payments received by one farmer."""
    with conn() as c:
        return c.execute(
            """SELECT p.*, o.buyer_name, o.qty_kg, l.crop, l.grade
               FROM payments p
               JOIN orders o   ON o.id = p.order_id
               JOIN listings l ON l.id = o.listing_id
               WHERE l.farmer_id = ?
               ORDER BY p.id DESC""", (fid,)).fetchall()


# ---------- donations ----------
def add_donation(donor, amount, txn_ref, note=""):
    with conn() as c:
        c.execute("INSERT INTO donations(donor,amount,txn_ref,note,created) VALUES(?,?,?,?,?)",
                  (donor, amount, txn_ref, note, _now()))


def all_donations():
    with conn() as c:
        return c.execute("SELECT * FROM donations ORDER BY id DESC").fetchall()


def donation_total():
    with conn() as c:
        return c.execute("SELECT COALESCE(SUM(amount),0) FROM donations").fetchone()[0]


# ---------- feedback ----------
def add_feedback(farmer_id, farmer_name, farmer_type, ease, price_fair,
                 paid_fast, wants, comment):
    with conn() as c:
        c.execute(
            "INSERT INTO feedback(farmer_id,farmer_name,farmer_type,ease,price_fair,"
            "paid_fast,wants,comment,created) VALUES(?,?,?,?,?,?,?,?,?)",
            (farmer_id, farmer_name, farmer_type, ease, price_fair,
             paid_fast, wants, comment, _now()))


def all_feedback():
    with conn() as c:
        return c.execute("SELECT * FROM feedback ORDER BY id DESC").fetchall()


def reset():
    """Wipe everything and reseed (handy for a fresh demo)."""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init(seed=True)
