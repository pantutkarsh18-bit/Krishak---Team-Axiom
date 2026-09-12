"""
payments.py  --  a SIMULATED UPI payment (no real money, no gateway)
====================================================================

Goal: show a realistic UPI payment on screen WITHOUT any real money moving
and WITHOUT paying for a payment gateway.

How we do that safely:

1. We build a normal UPI deep-link string, e.g.
       upi://pay?pa=<vpa>&pn=<name>&am=<amount>&cu=INR&tn=<note>
   and turn it into a QR code. This is exactly what real UPI QR codes look
   like, so it demos well.

2. The receiver id (VPA) we use ends in "@demo" — that is NOT a real bank
   handle, so even if someone scans it with a real UPI app, the app just
   says "invalid UPI ID" and nothing can be charged.

3. The actual "payment" happens with a button click inside the app. We only
   create a fake transaction reference and update a pretend wallet in our
   own database. Money never leaves anyone's bank.

So it looks and feels like UPI, but it is 100% a simulation for the demo.
"""

import io
import random
import string
import urllib.parse

import qrcode


def demo_vpa(farmer_name):
    """Make a clearly-fake UPI id for a farmer, e.g. 'ramesh.krishak@demo'."""
    handle = "".join(ch for ch in farmer_name.lower() if ch.isalnum()) or "farmer"
    return f"{handle}.krishak@demo"


def upi_link(vpa, payee_name, amount, note):
    """Build a standard UPI deep link (the text a UPI QR encodes)."""
    params = urllib.parse.urlencode({
        "pa": vpa,                    # payee address (the demo VPA)
        "pn": payee_name,             # payee name
        "am": f"{amount:.2f}",        # amount
        "cu": "INR",                  # currency
        "tn": note,                   # transaction note
    })
    return f"upi://pay?{params}"


def qr_png_bytes(data):
    """Return PNG bytes of a QR code for any text (here, the UPI link)."""
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def mock_txn_ref():
    """A pretend UPI transaction reference, e.g. 'SIMUPI4829105736'."""
    return "SIMUPI" + "".join(random.choices(string.digits, k=10))
