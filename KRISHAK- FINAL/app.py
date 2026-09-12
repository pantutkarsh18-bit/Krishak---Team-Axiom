"""
app.py  --  KisanSetu POC  (Streamlit)
======================================

Run:  streamlit run app.py

Three logins (all use username 'test' / password 'test', loaded from users.json):
  • Consumer -> shop the marketplace, add to a CART, checkout with simulated UPI
  • Farmer   -> list produce (quality-based pricing), see wallet & sales
  • Admin    -> dashboards across the whole platform

Payments are 100% simulated — no real money, no payment gateway.
"""

import os
import base64
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import db
import auth
import pricing
import payments

HERE = os.path.dirname(__file__)
db.init()

st.set_page_config(page_title="Krishak", page_icon="🌾", layout="wide")


# ---------------------------------------------------------------- helpers
def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

LOGO_B64 = b64(os.path.join(HERE, "assets", "logo.png"))
BG_B64 = b64(os.path.join(HERE, "assets", "bg.png"))
# full branded login hero (logo, tagline & story chips are baked into this image)
HERO_B64 = b64(os.path.join(HERE, "assets", "login_hero.jpg"))
# faint farm-texture background for the logged-in (inner) pages
INNER_B64 = b64(os.path.join(HERE, "assets", "inner_bg.jpg"))
# team group photo (shown at the bottom of the About → Team section)
TEAM_PHOTO_B64 = b64(os.path.join(HERE, "assets", "team_photo.jpg"))
# real product photos for shop cards (fall back to an emoji tile if not listed)
CROP_IMG = {"Onion": b64(os.path.join(HERE, "assets", "crop_onion.jpg")),
            "Tomato": b64(os.path.join(HERE, "assets", "crop_tomato.jpg")),
            "Rice": b64(os.path.join(HERE, "assets", "crop_rice.jpg")),
            "Banana": b64(os.path.join(HERE, "assets", "crop_banana.jpg")),
            "Potato": b64(os.path.join(HERE, "assets", "crop_potato.jpg"))}

GRADE_COLOR = {"A": "#1B7A43", "B": "#E8A317", "C": "#C0522A"}

# Display labels for roles. The INTERNAL role value stays "consumer" everywhere
# (auth, users.json, routing, db) — only the user-facing text changes.
ROLE_DISPLAY = {"consumer": "Retailer/Consumer", "farmer": "Farmer", "admin": "Admin"}
DISPLAY_TO_ROLE = {"Retailer/Consumer": "consumer", "Farmer": "farmer", "Admin": "admin"}


def inject_css():
    st.markdown(f"""
    <style>
      #MainMenu, footer {{visibility:hidden;}}
      .block-container {{padding-top:3rem; max-width:1250px;}}
      /* ---- 3D buttons ---- */
      .stButton>button {{
        border-radius:11px; font-weight:700; border:none;
        transition:transform .06s ease, box-shadow .06s ease, filter .12s ease;
      }}
      .stButton>button[kind="secondary"] {{
        background:#ffffff; color:#1F3D2B;
        box-shadow:0 4px 0 #cfd8d2, 0 8px 16px rgba(20,60,40,.18);
      }}
      .stButton>button[kind="secondary"]:hover {{filter:brightness(.99); box-shadow:0 4px 0 #cfd8d2, 0 10px 20px rgba(20,60,40,.24);}}
      .stButton>button[kind="secondary"]:active {{transform:translateY(4px); box-shadow:0 0 0 #cfd8d2, 0 3px 8px rgba(20,60,40,.20);}}
      .stButton>button[kind="primary"] {{
        background:linear-gradient(#25925a,#1B7A43); color:#fff;
        box-shadow:0 5px 0 #125e34, 0 9px 20px rgba(12,60,32,.34);
      }}
      .stButton>button[kind="primary"]:hover {{filter:brightness(1.05); box-shadow:0 5px 0 #125e34, 0 11px 24px rgba(12,60,32,.40);}}
      .stButton>button[kind="primary"]:active {{transform:translateY(5px); box-shadow:0 0 0 #125e34, 0 3px 8px rgba(12,60,32,.30);}}
      /* brand header */
      .ks-top {{display:flex; align-items:center; gap:14px; padding:10px 0 4px;}}
      .ks-top img {{height:46px;}}
      .ks-name {{font-size:26px; font-weight:800; color:#1F3D2B; letter-spacing:.2px; line-height:1.25;}}
      .ks-name span {{color:#1B7A43;}}
      .ks-tag {{color:#5A6672; font-size:13px; margin-top:-4px;}}
      /* login */
      .ks-hero-title {{font-size:40px; font-weight:800; color:#173A28; line-height:1.1; margin:6px 0;}}
      .ks-hero-title span {{color:#1B7A43;}}
      .ks-hero-sub {{color:#3f5147; font-size:16px;}}
      .ks-feat {{color:#2f4a3b; font-size:15px; margin:4px 0;}}
      /* product card */
      .ks-card {{border:1px solid #E3EBE2; border-radius:14px; padding:14px 14px 10px; background:#fff;
                 box-shadow:0 4px 14px rgba(30,80,50,.06); margin-bottom:10px;}}
      .ks-crop {{font-size:19px; font-weight:800; color:#1F3D2B;}}
      .ks-farmer {{color:#5A6672; font-size:13px;}}
      .ks-price {{font-size:22px; font-weight:800; color:#1B7A43;}}
      .ks-badge {{display:inline-block; padding:2px 10px; border-radius:12px; color:#fff;
                  font-size:12px; font-weight:700;}}
      .ks-pill {{display:inline-block; padding:3px 12px; border-radius:20px; background:#EDF5EA;
                 color:#1B7A43; font-weight:700; font-size:13px;}}
      /* ---- marketplace card (mockup style) ---- */
      .mk-thumb {{height:104px; border-radius:12px; display:flex; align-items:center;
                  justify-content:center; font-size:50px; margin-bottom:10px;}}
      .mk-verified {{color:#5A6672; font-size:12.5px; margin:3px 0 8px;}}
      .mk-share {{font-size:11.5px; color:#0d7a3e; background:#e7f6ec; border-radius:8px;
                  padding:6px 10px; margin:8px 0 2px; font-weight:600; text-align:center;}}
      /* ---- cart "you saved" banner ---- */
      .saved {{background:#e7f6ec; color:#0d7a3e; font-weight:700; font-size:14px;
               border-radius:10px; padding:11px 14px; text-align:center; margin:6px 0 4px;}}
      /* ---- payment split (the aha) ---- */
      .pay-you {{background:#1F3D2B; color:#fff; border-radius:14px; padding:16px 10px;
                 text-align:center; font-weight:700; font-size:15px;}}
      .pay-you b {{font-size:24px; display:block; margin-top:4px;}}
      .pay-w {{display:flex; align-items:center; gap:12px; background:#f7faf7;
               border:1px solid #E3EBE2; border-radius:12px; padding:11px 15px; margin-bottom:10px;}}
      .pay-w .av {{width:38px; height:38px; border-radius:50%; background:#EDF5EA;
                   display:flex; align-items:center; justify-content:center; font-size:20px;}}
      .pay-w .nm {{font-weight:700; color:#1F3D2B; font-size:14.5px;}}
      .pay-w .vg {{color:#5A6672; font-size:12px;}}
      .pay-w .cr {{margin-left:auto; color:#1B7A43; font-weight:800; font-size:16px;}}
      .pay-arrow {{color:#1B7A43; font-size:26px; text-align:center; font-weight:800;}}
      /* ---- farmer KPI + sparkline ---- */
      .fk {{border:1px solid #E3EBE2; border-radius:14px; padding:14px 16px; background:#fff;}}
      .fk .lab {{font-size:12px; color:#5A6672; font-weight:600;}}
      .fk .val {{font-size:25px; font-weight:800; color:#1F3D2B; margin-top:3px;}}
      .fk .val.g {{color:#1B7A43;}}
      .spark {{display:flex; align-items:flex-end; gap:6px; height:60px;}}
      .spark div {{flex:1; background:linear-gradient(#7fd3a0,#1B7A43); border-radius:4px 4px 0 0;}}
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------- login
_LOGIN_BG = """
<style>
/* ---------- split-panel login: farm story on the left, form on the right ---------- */
.stApp{background:#fdfdfb;}
[data-testid="stHeader"]{background:transparent;}

/* LEFT: fixed branded hero image (logo, tagline & story chips are baked in) */
.k-hero{position:fixed;left:0;top:0;width:56%;height:100vh;overflow:hidden;z-index:0;
  background:#0d3a1e;}
.k-hero img{width:100%;height:100%;object-fit:cover;object-position:left center;display:block;}
/* soft seam so the photo blends into the white form panel */
.k-hero::after{content:"";position:absolute;top:0;right:0;bottom:0;width:80px;
  background:linear-gradient(90deg,rgba(253,253,251,0),rgba(253,253,251,.9));}

/* RIGHT: the form column (this is Streamlit's own container) */
.stApp .block-container{position:relative;z-index:1;
  margin-left:56%;margin-right:0;width:44%;max-width:none;
  padding:clamp(38px,11vh,120px) clamp(22px,5.4vw,104px) 44px;}
.k-wb{font-size:25px;font-weight:800;color:#173A28;letter-spacing:.2px}
.k-wb-sub{font-size:13.5px;color:#7d8a83;margin-top:5px}
.k-role-h{font-weight:700;color:#54615a;font-size:12px;margin:18px 0 4px;letter-spacing:.3px}

/* role buttons -> compact segmented pills (they live inside st.columns) */
.stApp .block-container [data-testid="column"] .stButton>button{
  border-radius:999px;padding:9px 4px;font-size:12.5px;font-weight:700;
  white-space:nowrap !important;}
/* keep the button label on ONE line even in a narrow column */
.stApp .block-container [data-testid="column"] .stButton>button *{
  white-space:nowrap !important;font-size:11.5px;letter-spacing:-.2px;}

/* input polish */
.stApp .block-container .stTextInput [data-baseweb="input"]{border-radius:11px;background:#f7faf7;
  border:1px solid #dfe9e1;transition:border .15s, box-shadow .15s;}
.stApp .block-container .stTextInput [data-baseweb="input"]:focus-within{border-color:#1B7A43;
  box-shadow:0 0 0 3px rgba(27,122,67,.15);}

.k-foot{text-align:center;color:#93a09a;font-size:10.8px;margin-top:26px;letter-spacing:.2px}

/* ---------- responsive: stack the panels on tablet / mobile ---------- */
@media (max-width:900px){
  /* stack: show the whole branded image (no crop), form below */
  .k-hero{position:relative;width:auto;height:auto;min-height:0;
    margin:-26px -20px 18px;background:transparent;}
  .k-hero img{height:auto;object-fit:contain;object-position:center;}
  .k-hero::after{display:none;}
  .stApp .block-container{margin-left:0;width:100%;padding:6px 20px 34px;}
}
</style>
"""


def login_page():
    inject_css()
    ss = st.session_state
    ss.setdefault("login_role", "consumer")

    st.markdown(_LOGIN_BG, unsafe_allow_html=True)

    # ---- LEFT PANEL: the full branded hero image (all branding baked in) ----
    st.markdown(
        f'<div class="k-hero"><img src="data:image/jpeg;base64,{HERO_B64}" '
        f'alt="Krishak — one bridge, a fairer farm to market"></div>',
        unsafe_allow_html=True)

    # ---- RIGHT PANEL: the sign-in form ----
    st.markdown('<div class="k-wb">Welcome back</div>'
                '<div class="k-wb-sub">Sign in to your Krishak account</div>',
                unsafe_allow_html=True)

    st.markdown('<div class="k-role-h">I AM SIGNING IN AS</div>', unsafe_allow_html=True)
    roles = [("consumer", "🧺", "Retailer/Consumer"),
             ("farmer", "🌾", "Farmer"),
             ("admin", "⚙️", "Admin"),
             ("about", "ℹ️", "About")]
    for col, (rid, icon, lab) in zip(st.columns([1.7, 1, 1, 1]), roles):
        with col:
            selected = ss.login_role == rid
            if st.button(f"{icon} {lab}", key=f"lr_{rid}", use_container_width=True,
                         type=("primary" if selected else "secondary")):
                ss.login_role = rid
                st.rerun()

    # "About" is an open, no-login section — show the story instead of the sign-in form.
    if ss.login_role == "about":
        _about_krishak()
        st.markdown('<div class="k-foot">SIH 2026 &nbsp;·&nbsp; Problem Statement SIH26033 '
                    '&nbsp;·&nbsp; Team Axiom</div>', unsafe_allow_html=True)
        return

    # Farmers sign in either as an FPO (a farmer collective) or an individual.
    if ss.login_role == "farmer":
        ss.farmer_type = st.selectbox(
            "I am signing in as", ["FPO (Farmer Producer Organisation)", "Individual farmer"],
            help="An FPO manages produce for many member farmers; an individual manages their own.")

    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    lab = ROLE_DISPLAY[ss.login_role]
    if st.button(f"Login as {lab}", type="primary", use_container_width=True):
        if auth.authenticate(ss.login_role, username, password):
            st.session_state.auth = {"role": ss.login_role, "username": username,
                                     "farmer_type": ss.get("farmer_type", "Individual farmer")}
            st.session_state.cart = []
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.markdown('<div class="k-foot">SIH 2026 &nbsp;·&nbsp; Problem Statement SIH26033 '
                '&nbsp;·&nbsp; Team Axiom</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- top bar
def topbar():
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(
            f'<div class="ks-top"><img src="data:image/png;base64,{LOGO_B64}" alt="Krishak logo">'
            f'<div><div class="ks-name">Krish<span>ak</span></div>'
            f'<div class="ks-tag">Farm to Fork</div></div></div>',
            unsafe_allow_html=True)
    with c2:
        _r = st.session_state.auth['role']
        st.markdown(f"<div style='text-align:right;padding-top:8px'>"
                    f"<span class='ks-pill'>{ROLE_DISPLAY.get(_r, _r.title())} · "
                    f"{st.session_state.auth['username']}</span></div>", unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            st.session_state.auth = None
            st.session_state.cart = []
            st.rerun()
    st.divider()


# ---------------------------------------------------------------- cart utils
def cart_add(listing, qty):
    cart = st.session_state.cart
    for it in cart:
        if it["listing_id"] == listing["id"]:
            it["qty"] = min(it["qty"] + qty, listing["qty_kg"])
            return
    cart.append({
        "listing_id": listing["id"], "crop": listing["crop"], "grade": listing["grade"],
        "farmer": listing["farmer"], "farmer_id": listing["farmer_id"],
        "vpa": listing["vpa"], "price": listing["price_per_kg"], "qty": qty,
    })


def cart_total():
    return round(sum(i["price"] * i["qty"] for i in st.session_state.cart), 2)


def cart_count():
    return sum(i["qty"] for i in st.session_state.cart)


def _sidebar_cart():
    """A stylish live mini-cart in the sidebar — updates on every add."""
    cart = st.session_state.get("cart", [])
    n = cart_count()
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'margin:14px 0 8px"><span style="font-weight:800;color:#1F3D2B;font-size:14px">'
        f'🛒 Your cart</span>'
        f'<span style="background:#1B7A43;color:#fff;font-weight:800;font-size:11px;'
        f'padding:2px 9px;border-radius:20px">{int(n)} kg</span></div>',
        unsafe_allow_html=True)

    if not cart:
        st.markdown(
            '<div style="background:#f3f8f3;border:1px dashed #cfe0d3;border-radius:12px;'
            'padding:14px 12px;text-align:center;color:#8A94A0;font-size:12px">'
            'Cart is empty.<br>Add produce from the shop 🌾</div>',
            unsafe_allow_html=True)
        return

    rows = ""
    for it in cart:
        line = it["price"] * it["qty"]
        emo = pricing.crop_emoji(it["crop"])
        rows += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:7px 0;border-bottom:1px solid #eef2ee">'
            f'<span style="font-size:12px;color:#22302a">{emo} <b>{it["crop"]}</b>'
            f'<span style="color:#8A94A0"> · {it["qty"]:.0f} kg</span></span>'
            f'<span style="font-size:12.5px;font-weight:700;color:#1F3D2B">₹{line:,.0f}</span></div>')
    gross = cart_total()
    st.markdown(
        f'<div style="background:#fff;border:1px solid #e3ebe2;border-radius:14px;'
        f'padding:6px 13px 12px;box-shadow:0 6px 18px rgba(20,60,40,.08)">{rows}'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-top:10px;padding-top:9px;border-top:2px dashed #cdddd1">'
        f'<span style="font-size:12px;color:#5A6672;font-weight:700">Gross bill</span>'
        f'<span style="font-size:18px;font-weight:800;color:#1B7A43">₹{gross:,.2f}</span></div></div>',
        unsafe_allow_html=True)
    st.write("")
    if st.button("🧺  View cart & checkout", use_container_width=True, type="primary",
                 key="sb_viewcart"):
        st.session_state.cpage = "Cart"
        st.rerun()


# ---------------------------------------------------------------- CONSUMER
def consumer_app():
    ss = st.session_state
    ss.setdefault("cpage", "Shop")
    n = cart_count()
    a, bcol, ccol, _ = st.columns([1, 1, 1, 2])
    if a.button("🛒  Shop", use_container_width=True,
                type=("primary" if ss.cpage == "Shop" else "secondary")):
        ss.cpage = "Shop"; st.rerun()
    if bcol.button(f"🧺  Cart ({int(n)} kg)", use_container_width=True,
                   type=("primary" if ss.cpage == "Cart" else "secondary")):
        ss.cpage = "Cart"; st.rerun()
    if ccol.button("❤️  Donate", use_container_width=True,
                   type=("primary" if ss.cpage == "Donate" else "secondary")):
        ss.cpage = "Donate"; st.rerun()
    st.write("")
    if ss.cpage == "Cart":
        _cart_and_checkout()
    elif ss.cpage == "Donate":
        _donate_view()
    else:
        _shop_view()


def _donate_view():
    """Retailers can donate to a farmer-welfare fund, paid via simulated UPI."""
    ss = st.session_state
    done = ss.get("donation_done")
    if done:
        # ---- confirmation (same pattern as the order receipt) ----
        st.markdown(
            f'<div style="text-align:center;margin:6px 0 2px">'
            f'<div style="width:60px;height:60px;border-radius:50%;background:#e7f6ec;color:#1B7A43;'
            f'font-size:32px;display:flex;align-items:center;justify-content:center;margin:0 auto 8px">✓</div>'
            f'<div style="font-size:22px;font-weight:800;color:#1F3D2B">Thank you for donating '
            f'₹{done["amount"]:,.2f}! ❤️</div>'
            f'<div style="color:#5A6672;font-size:13.5px;margin-top:3px">Your contribution goes to the '
            f'Krishak farmer-welfare fund. &nbsp;Txn: <code>{done["txn"]}</code></div></div>',
            unsafe_allow_html=True)
        st.balloons()
        if st.button("Make another donation", type="primary"):
            ss.pop("donation_done", None)
            ss.pop("donate_amt_pending", None)
            st.rerun()
        return

    st.markdown("### ❤️ Support our farmers")
    st.caption("Donate any amount to the farmer-welfare fund — for tools, training, and "
               "crop-loss relief. Paid securely via UPI (simulated for this demo).")

    amt = st.number_input("Donation amount (₹)", min_value=1.0, value=100.0, step=50.0)
    quick = st.columns(4)
    for q, col in zip([100, 250, 500, 1000], quick):
        col.markdown(f"<div style='text-align:center;color:#5A6672;font-size:12px'>₹{q}</div>",
                     unsafe_allow_html=True)
    note = st.text_input("Message (optional)", placeholder="A word of encouragement for the farmers")

    if not ss.get("donate_amt_pending"):
        if st.button("❤️  Donate via UPI", type="primary", use_container_width=True):
            ss.donate_amt_pending = {"amount": round(amt, 2), "note": note}
            st.rerun()
    else:
        pend = ss.donate_amt_pending
        st.divider()
        st.subheader("Pay your donation — UPI (simulated)")
        link = payments.upi_link("krishak@demo", "Krishak Welfare Fund", pend["amount"],
                                 "Krishak donation")
        cqr, cinfo = st.columns([1, 1.4])
        with cqr:
            st.image(payments.qr_png_bytes(link), width=210, caption="Scan (demo QR)")
        with cinfo:
            st.write("**Pay to:** Krishak Welfare Fund  \n**UPI ID:** `krishak@demo`  "
                     "*(fake @demo id — cannot be charged)*")
            st.write(f"**Amount:** ₹{pend['amount']:,.2f}")
            st.code(link, language="text")
            ok, cancel = st.columns(2)
            if ok.button("✅ Confirm donation", type="primary"):
                txn = payments.mock_txn_ref()
                db.add_donation(st.session_state.auth["username"], pend["amount"], txn, pend["note"])
                ss.donation_done = {"amount": pend["amount"], "txn": txn}
                ss.pop("donate_amt_pending", None)
                st.rerun()
            if cancel.button("Cancel"):
                ss.pop("donate_amt_pending", None)
                st.rerun()


_THUMB_BG = {"🍅": "#fdeaea", "🧅": "#fbeee0", "🥔": "#eef7e6",
             "🌾": "#fbf3dd", "🍚": "#eef3f7", "🍌": "#fcf6d9"}


def farms_map():
    """A live, interactive Google Map (key-free embed) of a sourcing region."""
    farmers = db.all_farmers()
    villages = sorted({f["village"] for f in farmers}) or ["Nashik"]
    place = st.selectbox("Locate a sourcing region", villages, key="map_place")
    q = place.replace(" ", "+") + ",India"
    components.html(
        f'<iframe title="Krishak sourcing map" width="100%" height="340" '
        f'style="border:0;border-radius:14px" loading="lazy" '
        f'referrerpolicy="no-referrer-when-downgrade" '
        f'src="https://maps.google.com/maps?q={q}&z=11&output=embed"></iframe>',
        height=352)
    st.caption(f"Live Google Map · **{place}** — where this produce is grown. "
               f"Pan, zoom, or click to open in Google Maps.")


def _shop_view():
    st.markdown("### Fresh from the farm, today")
    st.caption("Buy directly from verified farmers — no middlemen, transparent pricing.")

    query = st.text_input(
        "search", key="shop_search", label_visibility="collapsed",
        placeholder="🔍  Search a product or farmer  (e.g. Onion, Tomato, Lakshmi…)")

    with st.expander("📍  Farms & pickup hubs near you", expanded=False):
        farms_map()
    market = db.list_market()
    if not market:
        st.info("No produce available right now.")
        return

    q = (query or "").strip().lower()
    if q:
        def _match(r):
            keys = r.keys()
            hay = " ".join(str(r[k]) for k in ("crop", "farmer", "village", "grade")
                           if k in keys)
            return q in hay.lower()
        market = [r for r in market if _match(r)]
        if not market:
            st.info(f"No produce or farmer matches “{query}”. Try another word.")
            return
        st.caption(f"Showing {len(market)} result{'s' if len(market) != 1 else ''} for “{query}”.")

    cols = st.columns(3, gap="medium")
    for i, r in enumerate(market):
        with cols[i % 3]:
            gc = GRADE_COLOR.get(r["grade"], "#666")
            emo = pricing.crop_emoji(r["crop"])
            price = r["price_per_kg"]
            got = pricing.farmer_payout(price)          # farmer's share of ₹1
            _img = CROP_IMG.get(r["crop"])
            if _img:
                thumb = (f'<div class="mk-thumb" style="padding:0;'
                         f'background:#000 center/cover url(data:image/jpeg;base64,{_img})"></div>')
            else:
                thumb = f'<div class="mk-thumb" style="background:{_THUMB_BG.get(emo, "#eef7e6")}">{emo}</div>'
            st.markdown(
                f'<div class="ks-card">'
                f'{thumb}'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span class="ks-crop">{r["crop"]}</span>'
                f'<span class="ks-badge" style="background:{gc}">Grade {r["grade"]}</span></div>'
                f'<div class="mk-verified">✔ {r["farmer"]} · {r["village"]}</div>'
                f'<div class="ks-price">₹{price:.0f}<span style="font-size:13px;color:#5A6672">/kg</span>'
                f'<span style="float:right;font-size:12px;color:#5A6672;padding-top:9px">{r["qty_kg"]:.0f} kg left</span></div>'
                f'<div class="mk-share">🌱 Farmer gets ₹{got:.2f} of every ₹{price:.0f}</div>'
                f'</div>', unsafe_allow_html=True)
            q = st.number_input("Qty (kg)", 1.0, float(r["qty_kg"]), 5.0, 1.0,
                                key=f"q_{r['id']}", label_visibility="collapsed")
            if st.button("➕  Add to cart", key=f"add_{r['id']}", use_container_width=True):
                cart_add(r, q)
                st.toast(f"Added {q:.0f} kg {r['crop']} to cart", icon="🛒")
                st.rerun()
            st.write("")


def _cart_and_checkout():
    receipt = st.session_state.get("receipt")
    if receipt:
        _cart_receipt(receipt)
        return

    cart = st.session_state.cart
    st.subheader("Your cart")
    if not cart:
        st.info("Your cart is empty — add some produce from the Shop tab.")
        return

    for idx, it in enumerate(list(cart)):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        c1.markdown(f"**{it['crop']}** · Grade {it['grade']}  \n"
                    f"<span style='color:#5A6672;font-size:13px'>{it['farmer']} · ₹{it['price']:.0f}/kg</span>",
                    unsafe_allow_html=True)
        newq = c2.number_input("kg", 1.0, 100000.0, float(it["qty"]), 1.0,
                               key=f"cq_{it['listing_id']}", label_visibility="collapsed")
        it["qty"] = newq
        c3.markdown(f"<div style='padding-top:6px'><b>₹{it['price']*it['qty']:.2f}</b></div>",
                    unsafe_allow_html=True)
        if c4.button("🗑", key=f"rm_{it['listing_id']}"):
            cart.remove(it)
            st.rerun()

    items = cart_total()
    delivery = pricing.delivery_fee(items)
    payable = round(items + delivery, 2)
    payout = pricing.farmer_payout(items)
    saving = pricing.retail_saving(items)
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Items subtotal", f"₹{items:,.2f}")
    m2.metric("Delivery", "FREE" if delivery == 0 else f"₹{delivery:,.2f}",
              "over ₹1,000" if delivery == 0 else "flat")
    m3.metric("Total payable", f"₹{payable:,.2f}")
    m4.metric("Farmers receive", f"₹{payout:,.2f}", "87% · direct")
    st.markdown(f'<div class="saved">💚 You saved ₹{saving:,.2f} vs the mandi retail price</div>',
                unsafe_allow_html=True)

    # ---------- delivery address (must be confirmed before paying) ----------
    ss = st.session_state
    ss.setdefault("addr_saved", False)
    a = ss.get("addr", {})
    st.divider()

    if not ss.addr_saved:
        st.markdown("#### 🚚 Delivery address")
        name = st.text_input("Full name", value=a.get("name", "Anita"))
        line = st.text_area("Address (house no., street, area / landmark)",
                            value=a.get("line", ""),
                            placeholder="Flat 2B, Green Residency, MG Road")
        c1, c2 = st.columns(2)
        city = c1.text_input("City / Town", value=a.get("city", ""))
        pin = c2.text_input("PIN code", value=a.get("pin", ""), max_chars=6)
        phone = st.text_input("Phone", value=a.get("phone", ""), max_chars=10)
        if st.button("✅  Save address & continue", type="primary"):
            if line.strip() and len(pin.strip()) >= 6 and pin.strip().isdigit():
                ss.addr = {"name": name.strip() or "Customer", "line": line.strip(),
                           "city": city.strip(), "pin": pin.strip(), "phone": phone.strip()}
                ss.addr_saved = True
                ss.addr_toast = True          # trigger the pop-up on next run
                st.rerun()
            else:
                st.warning("Please enter the full address and a valid 6-digit PIN code.")
    else:
        # one-time "Address accepted" pop-up (toast), then a persistent green card
        if ss.pop("addr_toast", False):
            st.toast("Address accepted", icon="✅")
        st.markdown(
            f'<div style="display:flex;gap:12px;align-items:flex-start;background:#e7f6ec;'
            f'border:1px solid #bfe3cc;border-radius:12px;padding:12px 15px;margin:2px 0 12px">'
            f'<div style="width:30px;height:30px;border-radius:50%;background:#1B7A43;color:#fff;'
            f'display:flex;align-items:center;justify-content:center;font-weight:800;flex:none;'
            f'font-size:16px">&#10003;</div>'
            f'<div style="font-size:13px;color:#22302a;line-height:1.5">'
            f'<b style="color:#0d7a3e">Address accepted</b> — delivering to<br>'
            f'<b>{a.get("name","")}</b>, {a.get("line","")}'
            f'{", " + a["city"] if a.get("city") else ""} — {a.get("pin","")}'
            f'{" &nbsp;·&nbsp; 📞 " + a["phone"] if a.get("phone") else ""}</div></div>',
            unsafe_allow_html=True)
        if st.button("✏️ Change address"):
            ss.addr_saved = False
            st.session_state.pop("checkout", None)
            st.rerun()
        st.session_state.checkout = {"buyer": a.get("name", "Customer"), "total": payable}
        _checkout_panel()


def _checkout_panel():
    co = st.session_state.get("checkout")
    if not co:
        return
    st.divider()
    st.subheader("💳 Pay for your order — UPI (simulated)")
    link = payments.upi_link("krishak@demo", "Krishak", co["total"],
                             f"Krishak cart · {cart_count():.0f}kg")
    a, b = st.columns([1, 1.4])
    with a:
        st.image(payments.qr_png_bytes(link), width=220, caption="Scan (demo QR)")
    with b:
        st.write("**Pay to:** Krishak  \n**UPI ID:** `krishak@demo`  *(fake @demo id — cannot be charged)*")
        st.write(f"**Amount:** ₹{co['total']:,.2f}")
        st.code(link, language="text")
        ok, cancel = st.columns(2)
        if ok.button("✅ Simulate UPI payment (success)", type="primary"):
            _settle_cart(co["buyer"])
        if cancel.button("Cancel"):
            del st.session_state.checkout
            st.session_state.addr_saved = False
            st.rerun()


def _settle_cart(buyer):
    """Create orders + simulated payments for every cart line, credit farmers."""
    txn = payments.mock_txn_ref()
    lines = []
    for it in st.session_state.cart:
        amount = round(it["price"] * it["qty"], 2)
        payout = pricing.farmer_payout(amount)
        oid = db.create_order(it["listing_id"], buyer, it["qty"], amount)
        db.mark_order_paid(oid)
        db.record_payment(oid, txn, amount, payout)
        db.credit_wallet(it["farmer_id"], payout)
        db.reduce_stock(it["listing_id"], it["qty"])
        lines.append({**it, "amount": amount, "payout": payout})
    items = round(sum(l["amount"] for l in lines), 2)
    delivery = pricing.delivery_fee(items)
    st.session_state.receipt = {
        "txn": txn, "buyer": buyer, "lines": lines,
        "items": items,
        "delivery": delivery,
        "total": round(items + delivery, 2),
        "payout": round(sum(l["payout"] for l in lines), 2),
        "inv": "KRK-" + txn[-8:],
        "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "address": dict(st.session_state.get("addr", {})),
    }
    st.session_state.cart = []
    st.session_state.pop("checkout", None)
    st.session_state.addr_saved = False     # re-ask address for the next order
    st.session_state.cpage = "Cart"     # stay on the cart page to show the receipt
    st.rerun()


def _invoice_inner(r):
    """Return the professional bill/invoice as an HTML block (inline styles)."""
    gross = r.get("items", r["total"])          # items subtotal
    delivery = r.get("delivery", 0.0)
    net = r["total"]                             # items + delivery
    plat = pricing.platform_cut(gross)
    trans = pricing.transport_cut(gross)
    farmers = r["payout"]
    logistics = round(trans + delivery, 2)       # transport share + delivery charge
    ad = r.get("address", {})
    addr_line = ad.get("line", "")
    if ad.get("city"):
        addr_line += ", " + ad["city"]
    if ad.get("pin"):
        addr_line += " — " + ad["pin"]
    addr_phone = (" · 📞 " + ad["phone"]) if ad.get("phone") else ""
    rows = ""
    for i, l in enumerate(r["lines"], 1):
        rows += (
            f'<tr>'
            f'<td style="padding:9px 8px;border-bottom:1px solid #eef2ee;color:#5A6672">{i}</td>'
            f'<td style="padding:9px 8px;border-bottom:1px solid #eef2ee;font-weight:600;color:#1F3D2B">'
            f'{l["crop"]} <span style="color:#8A94A0;font-weight:600">(Grade {l["grade"]})</span></td>'
            f'<td style="padding:9px 8px;border-bottom:1px solid #eef2ee;color:#5A6672">{l["farmer"]}</td>'
            f'<td style="padding:9px 8px;border-bottom:1px solid #eef2ee;text-align:right">{l["qty"]:.0f} kg</td>'
            f'<td style="padding:9px 8px;border-bottom:1px solid #eef2ee;text-align:right">&#8377;{l["price"]:.2f}</td>'
            f'<td style="padding:9px 8px;border-bottom:1px solid #eef2ee;text-align:right;font-weight:700;color:#1F3D2B">'
            f'&#8377;{l["amount"]:,.2f}</td></tr>')

    def tot(label, val, bold=False, color="#1F3D2B", big=False):
        fw = "800" if bold else "600"
        fs = "16px" if big else "13.5px"
        return (f'<tr><td style="padding:4px 0;color:#5A6672;font-size:{fs}">{label}</td>'
                f'<td style="padding:4px 0;text-align:right;font-weight:{fw};color:{color};'
                f'font-size:{fs}">&#8377;{val:,.2f}</td></tr>')

    return f'''
<div style="max-width:720px;margin:0 auto;background:#fff;border:1px solid #e3ebe2;border-radius:16px;
     padding:26px 30px;font-family:Segoe UI,Arial,sans-serif;color:#22302a;
     box-shadow:0 8px 30px rgba(20,60,40,.10)">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;
       border-bottom:2px solid #1B7A43;padding-bottom:14px">
    <div style="display:flex;align-items:center;gap:11px">
      <img src="data:image/png;base64,{LOGO_B64}" alt="Krishak" style="height:44px">
      <div><div style="font-size:22px;font-weight:800;color:#173A28">Krish<span style="color:#1B7A43">ak</span></div>
      <div style="font-size:11px;letter-spacing:2px;color:#1B7A43;font-weight:700">FARM TO FORK</div></div>
    </div>
    <div style="text-align:right">
      <div style="font-size:19px;font-weight:800;letter-spacing:1px;color:#1F3D2B">TAX INVOICE</div>
      <div style="font-size:12.5px;color:#5A6672;margin-top:3px">Invoice&nbsp;#: <b>{r["inv"]}</b></div>
      <div style="font-size:12.5px;color:#5A6672">Date: {r["date"]}</div>
    </div>
  </div>

  <div style="display:flex;justify-content:space-between;margin:16px 0 6px;font-size:12.5px">
    <div style="max-width:340px"><div style="color:#8A94A0;font-weight:700;letter-spacing:.5px">BILLED &amp; SHIPPED TO</div>
      <div style="font-weight:700;color:#1F3D2B;margin-top:2px">{r["buyer"]}</div>
      <div style="color:#5A6672">{addr_line}{addr_phone}</div>
      <div style="color:#8A94A0;font-size:11px">Retailer / Consumer · Krishak marketplace</div></div>
    <div style="text-align:right"><div style="color:#8A94A0;font-weight:700;letter-spacing:.5px">PAYMENT</div>
      <div style="color:#5A6672;margin-top:2px">Mode: UPI (simulated)</div>
      <div style="color:#5A6672">Txn Ref: {r["txn"]}</div>
      <div style="display:inline-block;margin-top:5px;background:#e7f6ec;color:#0d7a3e;font-weight:800;
           font-size:12px;padding:3px 12px;border-radius:20px;border:1px solid #bfe3cc">&#10003; PAID</div></div>
  </div>

  <table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:13px">
    <thead><tr style="background:#f3f8f3">
      <th style="padding:9px 8px;text-align:left;color:#33413a;font-size:11.5px;letter-spacing:.4px">#</th>
      <th style="padding:9px 8px;text-align:left;color:#33413a;font-size:11.5px;letter-spacing:.4px">ITEM</th>
      <th style="padding:9px 8px;text-align:left;color:#33413a;font-size:11.5px;letter-spacing:.4px">FARMER</th>
      <th style="padding:9px 8px;text-align:right;color:#33413a;font-size:11.5px;letter-spacing:.4px">QTY</th>
      <th style="padding:9px 8px;text-align:right;color:#33413a;font-size:11.5px;letter-spacing:.4px">RATE</th>
      <th style="padding:9px 8px;text-align:right;color:#33413a;font-size:11.5px;letter-spacing:.4px">AMOUNT</th>
    </tr></thead><tbody>{rows}</tbody>
  </table>

  <div style="display:flex;justify-content:space-between;gap:26px;margin-top:16px">
    <div style="flex:1;background:#f7faf7;border:1px solid #eef2ee;border-radius:12px;padding:12px 14px;
         font-size:11.5px;color:#5A6672;align-self:flex-start">
      <div style="font-weight:800;color:#33413a;letter-spacing:.4px;margin-bottom:6px">HOW THIS IS SETTLED</div>
      <div style="display:flex;justify-content:space-between;padding:2px 0">
        <span>&#128119; Farmers receive (87%)</span><b style="color:#1B7A43">&#8377;{farmers:,.2f}</b></div>
      <div style="display:flex;justify-content:space-between;padding:2px 0">
        <span>&#127981; Platform fee (5%)</span><span>&#8377;{plat:,.2f}</span></div>
      <div style="display:flex;justify-content:space-between;padding:2px 0">
        <span>&#128666; Logistics (8% + delivery)</span><span>&#8377;{logistics:,.2f}</span></div>
      <div style="display:flex;justify-content:space-between;padding:2px 0">
        <span>Middlemen</span><b>&#8377;0.00</b></div>
    </div>
    <table style="width:260px;border-collapse:collapse">
      {tot("Items subtotal", gross)}
      {tot("Delivery charge", delivery)}
      {tot("Taxes (GST @ 0%)", 0.0)}
      <tr><td colspan="2"><div style="border-top:1px dashed #cdddd1;margin:6px 0"></div></td></tr>
      {tot("Net payable", net, bold=True, color="#173A28", big=True)}
      {tot("Amount paid (UPI)", net, bold=True, color="#1B7A43")}
      {tot("Balance due", 0.0, bold=True)}
    </table>
  </div>

  <div style="border-top:1px solid #eef2ee;margin-top:16px;padding-top:10px;font-size:10.8px;color:#8A94A0;
       text-align:center">
    Computer-generated invoice · Payment simulated for the demo — no real money was transferred.<br>
    Krishak · SIH 2026 · Problem Statement SIH26033 · Team Axiom · Thank you for buying direct from farmers.
  </div>
</div>'''


def _invoice_download_html(r):
    inner = _invoice_inner(r)
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Krishak Invoice " + r["inv"] + "</title>"
            "<style>body{background:#eef4ee;margin:0;padding:24px}"
            "@media print{body{background:#fff;padding:0}}</style></head>"
            "<body>" + inner + "</body></html>")


def _cart_receipt(r):
    st.balloons()
    st.markdown(
        f'<div style="text-align:center;margin:6px 0 2px">'
        f'<div style="width:60px;height:60px;border-radius:50%;background:#e7f6ec;color:#1B7A43;'
        f'font-size:32px;display:flex;align-items:center;justify-content:center;margin:0 auto 8px">✓</div>'
        f'<div style="font-size:22px;font-weight:800;color:#1F3D2B">Payment successful — ₹{r["total"]:,.2f} paid</div>'
        f'<div style="color:#5A6672;font-size:13.5px;margin-top:3px">One payment, split instantly to every '
        f'farmer\'s wallet. &nbsp;Txn: <code>{r["txn"]}</code></div></div>',
        unsafe_allow_html=True)

    # ---- the payment-split fan-out (money going straight to each farmer) ----
    # combine cart lines by farmer so each farmer shows once
    by_farmer = {}
    for l in r["lines"]:
        f = by_farmer.setdefault(l["farmer_id"],
                                 {"name": l["farmer"], "payout": 0.0})
        f["payout"] += l["payout"]

    st.write("")
    left, mid, right = st.columns([1.1, 0.5, 1.6])
    with left:
        st.markdown(f'<div class="pay-you">🧺 You paid<b>₹{r["total"]:,.2f}</b></div>',
                    unsafe_allow_html=True)
    with mid:
        st.markdown('<div class="pay-arrow" style="padding-top:26px">➜➜➜</div>',
                    unsafe_allow_html=True)
    with right:
        for f in by_farmer.values():
            st.markdown(
                f'<div class="pay-w"><div class="av">👨‍🌾</div>'
                f'<div><div class="nm">{f["name"]}</div>'
                f'<div class="vg">wallet credited · direct</div></div>'
                f'<div class="cr">+₹{f["payout"]:,.2f}</div></div>',
                unsafe_allow_html=True)

    st.caption(f"Method: UPI (simulated — demo only) · Buyer: {r['buyer']} · "
               f"Middlemen took ₹0.")

    # ---------- professional bill / invoice ----------
    st.divider()
    st.markdown("### 🧾 Bill / Tax Invoice")
    st.markdown(_invoice_inner(r), unsafe_allow_html=True)
    st.write("")
    st.download_button("⬇️  Download bill (open & print to PDF)",
                       data=_invoice_download_html(r),
                       file_name=f"Krishak-Invoice-{r['inv']}.html",
                       mime="text/html")
    st.write("")
    if st.button("🛍 Continue shopping", type="primary"):
        del st.session_state.receipt
        st.session_state.cpage = "Shop"
        st.rerun()


# ---------------------------------------------------------------- FARMER
def farmer_app():
    farmers = db.all_farmers()
    names = {f'{f["name"]} — {f["village"]}': f["id"] for f in farmers}
    ftype = st.session_state.auth.get("farmer_type", "Individual farmer")
    is_fpo = ftype.startswith("FPO")

    if is_fpo:
        st.subheader("🏢 FPO console")
        st.markdown(
            f'<div class="ks-pill">Farmer Producer Organisation · aggregating for '
            f'{len(farmers)} member farmers</div>', unsafe_allow_html=True)
        st.write("")
        col, add = st.columns([2, 1])
        who = col.selectbox("Managing produce for member", list(names.keys()))
        with add.expander("➕ Add member farmer"):
            nn = st.text_input("Name", key="nfn")
            nv = st.text_input("Village", key="nfv")
            if st.button("Add member") and nn:
                db.add_farmer(nn, nv); st.rerun()
    else:
        st.subheader("👩‍🌾 Farmer console")
        col, add = st.columns([2, 1])
        who = col.selectbox("Viewing farmer", list(names.keys()), key="ind_farmer")
        with add.expander("➕ Add a farmer"):
            nn = st.text_input("Name", key="nfn_i")
            nv = st.text_input("Village", key="nfv_i")
            if st.button("Add farmer", key="addf_i") and nn:
                db.add_farmer(nn, nv); st.rerun()
        st.caption(f"Showing **{who.split(' — ')[0]}** · switch farmers to see each one's "
                   f"produce, sales and wallet status.")
    fid = names[who]
    farmer = db.get_farmer(fid)
    pays = db.payments_for_farmer(fid)

    kg_sold = sum(p["qty_kg"] for p in pays)
    avg_price = (sum(p["amount"] for p in pays) / kg_sold) if kg_sold else 0
    k1, k2, k3 = st.columns(3)
    k1.markdown(f'<div class="fk"><div class="lab">💰 Wallet (received direct)</div>'
                f'<div class="val g">₹{farmer["wallet"]:,.0f}</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="fk"><div class="lab">Sold so far</div>'
                f'<div class="val">{kg_sold:,.0f} kg</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="fk"><div class="lab">Avg. price realised</div>'
                f'<div class="val">₹{avg_price:,.0f}/kg</div></div>', unsafe_allow_html=True)
    st.caption(f"Direct UPI id: `{farmer['vpa']}`  ·  no middlemen between you and the buyer")

    # earnings sparkline — last few payouts
    if pays:
        vals = [p["farmer_payout"] for p in list(pays)[:7]][::-1]
        mx = max(vals) or 1
        bars = "".join(f'<div style="height:{max(8, v/mx*100):.0f}%"></div>' for v in vals)
        st.markdown(f'<div style="font-size:13px;color:#5A6672;margin:10px 0 4px">Recent earnings</div>'
                    f'<div class="spark">{bars}</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📦 My produce", "💵 Sales received", "🗣 Feedback"])
    with tab1:
        st.markdown("**List new produce**")
        c1, c2, c3, c4 = st.columns(4)
        crop = c1.selectbox("Crop", list(pricing.BENCHMARK.keys()))
        grade = c2.selectbox("Grade", ["A", "B", "C"], help="A=full price, B=85%, C=70%")
        qty = c3.number_input("Qty (kg)", 1.0, value=100.0, step=10.0)
        sug = pricing.suggested_price(crop, grade)
        price = c4.number_input("₹/kg", 1.0, value=float(sug), step=1.0)
        st.caption(f"📌 e-NAM benchmark {crop}: ₹{pricing.BENCHMARK[crop]}/kg · "
                   f"suggested Grade {grade}: **₹{sug}/kg** (quality-based)")
        if st.button("List produce", type="primary"):
            db.add_listing(fid, crop, grade, qty, price); st.success("Listed!"); st.rerun()
        st.markdown("**Current listings**")
        mine = db.listings_by_farmer(fid)
        if mine:
            st.dataframe(pd.DataFrame([{"ID": r["id"], "Crop": r["crop"], "Grade": r["grade"],
                "Left (kg)": r["qty_kg"], "₹/kg": r["price_per_kg"]} for r in mine]),
                use_container_width=True, hide_index=True)
        else:
            st.write("No listings yet.")
    with tab2:
        if pays:
            st.dataframe(pd.DataFrame([{"Txn": p["txn_ref"], "Buyer": p["buyer_name"],
                "Item": f'{p["qty_kg"]:.0f}kg {p["crop"]} (G{p["grade"]})',
                "You received ₹": p["farmer_payout"], "When": p["created"]} for p in pays]),
                use_container_width=True, hide_index=True)
        else:
            st.info("No sales yet.")
    with tab3:
        _farmer_feedback(fid, farmer["name"], ftype)


def _farmer_feedback(fid, fname, ftype):
    """A short form that helps farmers get more out of Krishak."""
    ss = st.session_state
    if ss.get(f"fb_done_{fid}"):
        st.success("🙏 Thank you! Your feedback helps us build Krishak around your needs.")
        if st.button("Submit another response"):
            ss.pop(f"fb_done_{fid}", None); st.rerun()
        return

    st.markdown("**Help us serve you better** — a few quick questions:")
    ease = st.slider("How easy is it to list your produce and get paid?  (1 = hard, 5 = very easy)",
                     1, 5, 4)
    price_fair = st.radio("Do the prices you get on Krishak feel fair?",
                          ["Yes, better than before", "About the same", "No, still low"],
                          horizontal=True)
    paid_fast = st.radio("Did the money reach your account quickly?",
                         ["Yes, instantly", "Within a day", "It was slow"], horizontal=True)
    wants = st.multiselect(
        "What would help you most? (pick any)",
        ["Guaranteed price before harvest", "Crop-quality tips", "Weather & mandi price alerts",
         "Transport pickup from my farm", "Loans / working capital", "Bulk buyer connections"])
    comment = st.text_area("Anything else you'd like us to add or fix?",
                           placeholder="Your suggestions in your own words…")
    if st.button("Submit feedback", type="primary"):
        db.add_feedback(fid, fname, ftype, ease, price_fair, paid_fast,
                        ", ".join(wants), comment)
        ss[f"fb_done_{fid}"] = True
        st.rerun()


# ---------------------------------------------------------------- ADMIN
def admin_app():
    st.subheader("📊 Admin dashboard")
    pays = db.all_payments()
    ov, pt, fl, fb = st.tabs(["Overview", "Payments", "Farmers & Listings", "Feedback & Donations"])

    with ov:
        if not pays:
            st.info("No sales yet — log in as a Retailer/Consumer and buy something.")
        else:
            gmv = round(sum(p["amount"] for p in pays), 2)
            to_f = round(sum(p["farmer_payout"] for p in pays), 2)
            platform = round(sum(pricing.platform_cut(p["amount"]) for p in pays), 2)   # 5%
            transport = round(sum(pricing.transport_cut(p["amount"]) for p in pays), 2)  # 8%
            trad_f = round(sum(pricing.traditional_farmer_share(p["amount"]) for p in pays), 2)
            trad_m = round(gmv - trad_f, 2)
            extra = round(to_f - trad_f, 2)
            mult = (to_f / trad_f) if trad_f else 0
            donated = round(db.donation_total(), 2)

            n_farm = len(db.all_farmers())
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="fk"><div class="lab">💼 Platform earned (5% fee)</div>'
                        f'<div class="val g">₹{platform:,.2f}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="fk"><div class="lab">🚚 Transport collected (8%)</div>'
                        f'<div class="val">₹{transport:,.2f}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="fk"><div class="lab">Returned to farmers</div>'
                        f'<div class="val g">₹{to_f:,.0f}</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="fk"><div class="lab">❤️ Donations received</div>'
                        f'<div class="val g">₹{donated:,.0f}</div></div>', unsafe_allow_html=True)
            st.caption(f"{len(pays)} orders settled · {n_farm} farmers onboarded")
            st.write("")

            st.markdown("#### Where every ₹ of sales goes")

            # a vivid, eye-friendly palette shared by both pies
            PIE_COLORS = {"Farmer": "#16A34A", "Middlemen": "#EF4444",
                          "Transport": "#F59E0B", "Platform": "#6366F1"}

            def donut(segs, total):
                """Draw one colourful donut pie of a ₹ split, with % labels."""
                df = pd.DataFrame([{"Who": w, "₹": round(v, 2),
                                    "pct": (v / total * 100 if total else 0),
                                    "lbl": f"{(v/total*100 if total else 0):.0f}%"}
                                   for w, v in segs])
                base = alt.Chart(df).encode(
                    theta=alt.Theta("₹:Q", stack=True),
                    color=alt.Color("Who:N",
                                    scale=alt.Scale(domain=list(PIE_COLORS.keys()),
                                                    range=list(PIE_COLORS.values())),
                                    legend=alt.Legend(orient="bottom", title=None,
                                                      labelFontSize=13)),
                    order=alt.Order("₹:Q", sort="descending"),
                    tooltip=["Who:N", alt.Tooltip("₹:Q", format=",.0f"),
                             alt.Tooltip("pct:Q", title="share %", format=".0f")])
                arc = base.mark_arc(innerRadius=60, outerRadius=108,
                                    stroke="#fff", strokeWidth=3)
                labels = base.mark_text(radius=134, fontSize=15, fontWeight="bold").encode(
                    text=alt.Text("lbl:N"), color=alt.value("#334155"))
                return (arc + labels).properties(height=320).configure_view(strokeWidth=0)

            g1, g2 = st.columns(2)
            with g1:
                st.markdown("<div style='text-align:center;font-weight:800;color:#1F3D2B;"
                            "font-size:16px'>🚜 Traditional chain</div>", unsafe_allow_html=True)
                st.altair_chart(donut([("Farmer", trad_f), ("Middlemen", trad_m)], gmv),
                                use_container_width=True)
                st.caption(f"Farmer keeps only **₹{trad_f:,.0f}** · middlemen take **₹{trad_m:,.0f}**")
            with g2:
                st.markdown("<div style='text-align:center;font-weight:800;color:#1B7A43;"
                            "font-size:16px'>🌾 With Krishak</div>", unsafe_allow_html=True)
                st.altair_chart(donut([("Farmer", to_f), ("Transport", transport),
                                       ("Platform", platform)], gmv),
                                use_container_width=True)
                st.caption(f"Farmer keeps **₹{to_f:,.0f}** (87%) · transport **₹{transport:,.0f}** · "
                           f"platform **₹{platform:,.0f}** · middlemen **₹0**")

            st.markdown(
                f"<div class='saved'>👩‍🌾 On Krishak farmers keep <b>₹{to_f:,.0f}</b> vs about "
                f"<b>₹{trad_f:,.0f}</b> traditionally — that's <b>₹{extra:,.0f} more (~{mult:.1f}×)</b> "
                f"reaching the people who grow the food.</div>", unsafe_allow_html=True)
    with pt:
        if pays:
            st.dataframe(pd.DataFrame([{"Txn": p["txn_ref"], "Buyer": p["buyer_name"],
                "Item": f'{p["qty_kg"]:.0f}kg {p["crop"]} (G{p["grade"]})',
                "Amount ₹": p["amount"], "Farmer got ₹": p["farmer_payout"],
                "Platform ₹": pricing.platform_cut(p["amount"]),
                "Transport ₹": pricing.transport_cut(p["amount"]),
                "Farmer": p["farmer"], "When": p["created"]} for p in pays]),
                use_container_width=True, hide_index=True)
        else:
            st.info("No payments yet.")
    with fl:
        st.markdown("#### Farmers & wallets")
        st.dataframe(pd.DataFrame([{"Farmer": f["name"], "Village": f["village"],
            "UPI id": f["vpa"], "Wallet ₹": f["wallet"]} for f in db.all_farmers()]),
            use_container_width=True, hide_index=True)
        st.markdown("#### Live listings")
        st.dataframe(pd.DataFrame([{"Crop": r["crop"], "Grade": r["grade"],
            "Left (kg)": r["qty_kg"], "₹/kg": r["price_per_kg"], "Farmer": r["farmer"]}
            for r in db.list_market()]), use_container_width=True, hide_index=True)
    with fb:
        st.markdown("#### 🗣 Farmer feedback")
        fbs = db.all_feedback()
        if fbs:
            st.dataframe(pd.DataFrame([{"Farmer": f["farmer_name"], "Type": f["farmer_type"],
                "Ease (1-5)": f["ease"], "Prices fair?": f["price_fair"],
                "Paid fast?": f["paid_fast"], "Wants": f["wants"],
                "Comment": f["comment"], "When": f["created"]} for f in fbs]),
                use_container_width=True, hide_index=True)
        else:
            st.info("No feedback submitted yet — log in as a Farmer and use the Feedback tab.")
        st.markdown("#### ❤️ Donations received")
        dons = db.all_donations()
        if dons:
            st.dataframe(pd.DataFrame([{"Donor": d["donor"], "Amount ₹": d["amount"],
                "Message": d["note"], "Txn": d["txn_ref"], "When": d["created"]} for d in dons]),
                use_container_width=True, hide_index=True)
            st.caption(f"Total donated: **₹{db.donation_total():,.2f}**")
        else:
            st.info("No donations yet — log in as a Retailer/Consumer and use the Donate tab.")


# ---------------------------------------------------------------- ABOUT
def _about_krishak():
    st.markdown("""
<style>
.ab-hero{
  position:relative; border-radius:24px; overflow:hidden;
  padding:46px 40px 40px; margin:6px 0 26px;
  background:linear-gradient(120deg,#0B3D24 0%,#15803D 48%,#22A24C 100%);
  box-shadow:0 20px 50px rgba(8,42,22,.30);}
.ab-hero::after{content:"🌾"; position:absolute; right:26px; bottom:-14px;
  font-size:128px; opacity:.14; transform:rotate(-8deg);}
.ab-eyebrow{display:inline-block; letter-spacing:.28em; font-size:12px; font-weight:800;
  text-transform:uppercase; color:#BBF7D0; background:rgba(255,255,255,.12);
  padding:6px 14px; border-radius:999px; margin-bottom:16px;}
.ab-hero .ab-title{margin:0; font-size:clamp(34px,5vw,54px); font-weight:900;
  line-height:1.05; color:#ffffff !important; letter-spacing:-.5px;}
.ab-hero .ab-title .g{background:linear-gradient(90deg,#FDE68A,#FEF9C3);
  -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color:transparent; color:transparent !important;}
.ab-tag{margin:14px 0 0; font-size:19px; font-weight:500; color:#E7F6EC; max-width:640px;}
.ab-lead{font-size:17px; line-height:1.75; color:#274536; margin:2px 0 22px;}
.ab-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:16px;}
.ab-card{background:#fff; border:1px solid #E3EBE4; border-left:5px solid #16A34A;
  border-radius:16px; padding:20px 20px 18px; box-shadow:0 10px 26px rgba(8,42,22,.08);}
.ab-ic{font-size:30px; line-height:1;}
.ab-h{font-weight:800; color:#123D26; font-size:17px; margin:10px 0 6px;}
.ab-p{color:#51665A; font-size:14px; line-height:1.6; margin:0;}
.ab-strip{display:flex; flex-wrap:wrap; gap:14px; margin:26px 0 6px;}
.ab-stat{flex:1 1 160px; background:linear-gradient(180deg,#F2FBF4,#EAF7ED);
  border:1px solid #CDEAD6; border-radius:16px; padding:18px 20px; text-align:center;}
.ab-num{font-size:30px; font-weight:900; color:#15803D; line-height:1;}
.ab-lab{font-size:12.5px; color:#4B6152; margin-top:6px; font-weight:600;}
</style>

<div class="ab-hero">
  <span class="ab-eyebrow">🌱 Farm to Fork · Direct</span>
  <h1 class="ab-title">About <span class="g">Krishak</span></h1>
  <p class="ab-tag">One bridge, a fairer farm to market — connecting the people who
     grow our food directly with the people who buy it.</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<p class="ab-lead">
<b>Krishak</b> is a direct farmer-to-consumer marketplace built to remove the long chain
of middlemen that eats into a farmer's earnings and inflates prices for buyers. On the
traditional chain a farmer often keeps only about a third of what you pay. Krishak puts
<b>87% back in the farmer's hands</b> — with transparent, quality-based pricing and instant
digital settlement — so growers earn more and buyers still pay a fair price.
</p>
""", unsafe_allow_html=True)

    _team_section()

    st.markdown("#### What Krishak does")
    st.markdown("""
<div class="ab-grid">
  <div class="ab-card"><div class="ab-ic">🛒</div>
    <div class="ab-h">A direct marketplace</div>
    <p class="ab-p">Buyers shop fresh produce straight from verified farmers and FPOs —
       real photos, real grades, no middlemen in between.</p></div>
  <div class="ab-card"><div class="ab-ic">💰</div>
    <div class="ab-h">Transparent pricing</div>
    <p class="ab-p">Every listing shows exactly how much of your rupee reaches the farmer,
       with fair prices set by crop quality and grade.</p></div>
  <div class="ab-card"><div class="ab-ic">⚡</div>
    <div class="ab-h">Instant UPI settlement</div>
    <p class="ab-p">A single payment at checkout is split automatically and settled
       straight into each farmer's wallet — no waiting, no deductions.</p></div>
  <div class="ab-card"><div class="ab-ic">🤝</div>
    <div class="ab-h">FPO aggregation</div>
    <p class="ab-p">Farmer Producer Organisations pool many small farmers together, giving
       them scale, shared logistics and a stronger voice in the market.</p></div>
  <div class="ab-card"><div class="ab-ic">🚚</div>
    <div class="ab-h">Shared logistics</div>
    <p class="ab-p">Pickup hubs and a small transparent transport fee move produce from
       farm to buyer efficiently, without hidden costs.</p></div>
  <div class="ab-card"><div class="ab-ic">❤️</div>
    <div class="ab-h">Farmer-welfare fund</div>
    <p class="ab-p">Buyers can donate to a welfare fund, and farmers share feedback that
       helps Krishak keep improving for the community.</p></div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="ab-strip">
  <div class="ab-stat"><div class="ab-num">87%</div><div class="ab-lab">reaches the farmer</div></div>
  <div class="ab-stat"><div class="ab-num">0</div><div class="ab-lab">middlemen in the chain</div></div>
  <div class="ab-stat"><div class="ab-num">3</div><div class="ab-lab">roles: Farmer · Buyer · Admin</div></div>
  <div class="ab-stat"><div class="ab-num">UPI</div><div class="ab-lab">instant direct settlement</div></div>
</div>
""", unsafe_allow_html=True)

    st.caption("SIH 2026 · Problem Statement SIH26033 · Team Axiom")


def _team_section():
    members = [
        ("Suyash Chandra Tripathi", "stripathi2_be26@thapar.edu"),
        ("Utkarsh Pant", "upant_be26@thapar.edu"),
        ("Tamanna Gupta", "ttamanna_be26@thapar.edu"),
        ("Tejal Arora", "tarora1_be26@thapar.edu"),
        ("Shashwat Prakash", "sprakash_be26@thapar.edu"),
        ("Mukul Joshi", "mjoshi_be26@thapar.edu"),
    ]

    def _initials(n):
        parts = [p for p in n.split() if p]
        return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()

    st.markdown("""
<style>
.tm-head{display:flex; align-items:center; gap:12px; margin:30px 0 6px;}
.tm-head h3{margin:0; font-size:24px; font-weight:900; color:#123D26; letter-spacing:-.3px;}
.tm-head .bar{width:6px; height:26px; border-radius:6px;
  background:linear-gradient(180deg,#22A24C,#0B3D24);}
.tm-head .pill{margin-left:auto; font-size:12px; font-weight:800; color:#15803D;
  background:#EAF7ED; border:1px solid #CDEAD6; padding:4px 12px; border-radius:999px;}
.tm-sub{color:#51665A; font-size:14px; margin:2px 0 18px;}
.tm-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px;}
.tm-card{display:flex; align-items:center; gap:14px; background:#fff;
  border:1px solid #E3EBE4; border-radius:16px; padding:14px 16px;
  box-shadow:0 8px 22px rgba(8,42,22,.07); transition:transform .15s, box-shadow .15s;}
.tm-card:hover{transform:translateY(-2px); box-shadow:0 14px 30px rgba(8,42,22,.12);}
.tm-av{flex:0 0 auto; width:46px; height:46px; border-radius:50%;
  background:linear-gradient(135deg,#22A24C,#0B3D24); color:#fff; font-weight:800;
  font-size:16px; display:flex; align-items:center; justify-content:center;
  box-shadow:0 4px 10px rgba(11,61,36,.30);}
.tm-info{min-width:0;}
.tm-name{font-weight:800; color:#173A28; font-size:15px; line-height:1.2;}
.tm-mail{font-size:12.5px; color:#4B6152; margin-top:3px; word-break:break-all;}
.tm-mail a{color:#15803D; text-decoration:none;}
.tm-mail a:hover{text-decoration:underline;}
</style>
""", unsafe_allow_html=True)

    st.markdown(
        '<div class="tm-head"><span class="bar"></span><h3>Team Members</h3>'
        f'<span class="pill">👥 {len(members)} members</span></div>'
        '<p class="tm-sub">The people behind Krishak.</p>',
        unsafe_allow_html=True)

    cards = ""
    for name, mail in members:
        cards += (
            f'<div class="tm-card"><div class="tm-av">{_initials(name)}</div>'
            f'<div class="tm-info"><div class="tm-name">{name}</div>'
            f'<div class="tm-mail">✉️ <a href="mailto:{mail}">{mail}</a></div>'
            f'</div></div>')
    st.markdown(f'<div class="tm-grid">{cards}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="margin:20px 0 4px;border-radius:18px;overflow:hidden;'
        'border:1px solid #E3EBE4;box-shadow:0 14px 34px rgba(8,42,22,.16);'
        'background:#0B3D24">'
        f'<img src="data:image/jpeg;base64,{TEAM_PHOTO_B64}" alt="Team Axiom together" '
        'style="display:block;width:100%;height:auto"></div>'
        '<div style="text-align:center;color:#51665A;font-size:12.5px;'
        'margin:8px 0 2px">📸 Team Axiom — building Krishak together</div>',
        unsafe_allow_html=True)


# ---------------------------------------------------------------- main
# a subtle farm-texture wash behind every logged-in page (content stays readable)
_INNER_BG = """
<style>
/* image clearly visible page-wide */
.stApp{background:linear-gradient(rgba(6,30,18,.20),rgba(6,30,18,.30)),
       url(data:image/jpeg;base64,__BG__) center top/cover fixed !important;}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stSidebar"]{background:rgba(233,242,231,.72);backdrop-filter:blur(6px);}
/* content floats on a soft frosted-white panel over the photo */
.stApp .block-container{
  background:rgba(255,255,255,.82);
  backdrop-filter:blur(9px); -webkit-backdrop-filter:blur(9px);
  border:1px solid rgba(255,255,255,.55);
  border-radius:22px;
  box-shadow:0 22px 64px rgba(8,32,18,.30);
  padding:2.2rem 2.4rem 2.6rem !important;
  margin-top:1.4rem; margin-bottom:2rem;}
</style>
"""


def main():
    st.session_state.setdefault("auth", None)
    st.session_state.setdefault("cart", [])

    if not st.session_state.auth:
        login_page()
        return

    inject_css()
    st.markdown(_INNER_BG.replace("__BG__", INNER_B64), unsafe_allow_html=True)
    topbar()
    role = st.session_state.auth["role"]
    with st.sidebar:
        st.markdown(f'<img src="data:image/png;base64,{LOGO_B64}" alt="Krishak logo" style="height:40px">',
                    unsafe_allow_html=True)
        st.caption("Krishak")
        if role == "consumer":
            _sidebar_cart()
        if st.button("🔄 Reset demo data", use_container_width=True):
            db.reset()
            for k in ("cart", "checkout", "receipt"):
                st.session_state.pop(k, None)
            st.rerun()

    if role == "consumer":
        consumer_app()
    elif role == "farmer":
        farmer_app()
    else:
        admin_app()


main()
