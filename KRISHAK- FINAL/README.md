# 🌾 Krishak — Farm to Fork, Direct (POC)

A student **proof-of-concept** for SIH 2026, PS **SIH26033** —
*"Multiple intermediaries reduce farmers' earnings and increase consumer prices."*

Krishak is a small farmer-to-consumer marketplace that **removes the
middlemen**. It now has a **branded login**, **three roles**, a real
**shopping-cart checkout**, and a **simulated UPI payment** — all in Python.

---

## 1. Logins (3 roles)

The app opens on a login page. All three accounts use the same demo password:

| Role | Username | Password | What they see |
|------|----------|----------|----------------|
| **Retailer/Consumer** | `krishak@123` | `krishak@123` | Shop → **cart** → simulated-UPI checkout, plus a **Donate** tab |
| **Farmer** | `krishak@123` | `krishak@123` | Sign in as an **FPO** or **individual**; list produce, wallet, sales, feedback |
| **Admin** | `krishak@123` | `krishak@123` | Dashboards, fee split (pie charts), feedback & donations |

**Fee split:** each sale is transparent — the farmer keeps **87%**, with a **5% platform fee**
and an **8% transport/logistics fee** (vs ~33% to the farmer in the middleman chain).

> 🔑 The usernames/passwords are **not hardcoded in the Python**. They live in
> **`users.json`** and are read by `auth.py`. Change that file to change the
> accounts. (A real app would store password *hashes* there and use HTTPS.)

---

## 2. How to run it

You need **Python 3.9+**.

```bash
pip install -r requirements.txt
streamlit run app.py
```

**Try this demo path:**
1. Login as **Consumer** (`krishak@123` / `krishak@123`).
2. On **Shop**, add a couple of items to the cart.
3. Open **Cart**, review the totals, click **Proceed to checkout**.
4. Click **Simulate UPI payment** → see the order receipt.
5. Logout, login as **Admin** to see the impact dashboard.

Use **🔄 Reset demo data** (sidebar) to start fresh.

---

## 3. The shopping cart (e-commerce style)

Consumers don't pay item-by-item. They **add items to a cart** (from any
farmer), adjust quantities, remove items, and then **checkout the whole cart in
one payment** — just like Amazon/Flipkart. At checkout the single payment is
**split** and settled to each farmer's wallet automatically.

---

## 4. The "UPI payment" — simulated, no real money, no gateway

The task was to show a UPI payment **without any real money moving and without
buying a payment gateway.** Three safety layers make that safe:

1. **Real-looking UPI QR.** We build a standard `upi://pay?...` deep link and
   render it as a QR — exactly what real UPI QRs look like.
2. **A fake receiver id.** The UPI id ends in `@demo`. `@demo` is **not** a
   real bank handle, so even if scanned, a real UPI app says *"invalid UPI ID"* —
   **nothing can be charged.**
3. **The payment is a button, not a bank transfer.** "Simulate UPI payment" only
   creates a fake txn reference (`SIMUPI…`), marks the order paid, and credits
   each farmer's **pretend wallet** in the local database.

To go live later you swap **only** this one step for a real UPI API — everything
else stays the same.

---

## 5. The files

| File | What it does |
|------|--------------|
| `app.py` | The Streamlit app: login gate, shop, cart, checkout, role dashboards. |
| `auth.py` | Reads `users.json` and checks the login. |
| `users.json` | The login accounts (username/password) — **edit here, not in code**. |
| `db.py` | SQLite database — farmers, listings, orders, payments. |
| `pricing.py` | Transparent + quality-based pricing (price by grade). |
| `payments.py` | The **simulated UPI**: UPI link, QR, fake txn ref. |
| `assets/` | Logo + login hero image. |
| `.streamlit/config.toml` | Green theme. |
| `requirements.txt` | Libraries to install. |

`kisansetu.db` is created automatically on first run and re-seeded with demo
farmers. Delete it (or hit **Reset demo data**) to start over.

---

## 6. Maps to the deck

This POC is the working core of the **Technical Approach** slide:
Streamlit UI · SQLite data · pandas dashboard · qrcode for UPI — all Python.
The **quality-based pricing** and **direct UPI payout** are the same features on
the **Future Roadmap** slide — here you can click through them.

*Note: the ~⅓ farmer-share figure in the comparison is illustrative, based on
published studies of India's farm-to-retail price spread.*
