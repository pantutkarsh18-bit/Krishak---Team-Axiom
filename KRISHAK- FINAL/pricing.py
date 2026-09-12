"""
pricing.py  --  transparent, quality-based pricing (the fairness engine)
========================================================================

Two simple ideas the whole project is built on:

1. TRANSPARENT PRICE
   Every crop has a public reference ("benchmark") price, like the mandi /
   e-NAM rate. We start from that instead of a middleman's secret quote.

2. QUALITY-BASED PRICE
   Better quality earns a better price. Grade A gets the full benchmark,
   Grade B a bit less, Grade C less again. (This is the "price by grade"
   feature from the roadmap.)
"""

# Reference / benchmark price in Rupees per kg (pretend these came from e-NAM).
BENCHMARK = {
    "Tomato": 30, "Onion": 25, "Potato": 20,
    "Wheat": 28, "Rice": 45, "Banana": 40,
}

# How much of the benchmark each quality grade earns.
GRADE_FACTOR = {"A": 1.00, "B": 0.85, "C": 0.70}

# Krishak keeps two small, transparent fees out of each sale:
PLATFORM_FEE = 0.05          # 5% to run the platform (tech, payments, support)
TRANSPORT_FEE = 0.08         # 8% for logistics — pickup & delivery from farm to buyer
# ...so the farmer still keeps 87% (vs ~a third in the middleman chain).

TRAD_FARMER_SHARE = 0.33     # in the old middleman chain, farmer gets ~a third
RETAIL_MARKUP = 0.38         # a shopper pays ~38% more in the middleman retail chain

# A friendly picture for each crop, used on the shop cards.
CROP_EMOJI = {
    "Tomato": "🍅", "Onion": "🧅", "Potato": "🥔",
    "Wheat": "🌾", "Rice": "🍚", "Banana": "🍌",
}


def crop_emoji(crop):
    return CROP_EMOJI.get(crop, "🥬")


def suggested_price(crop, grade):
    """Suggested fair ₹/kg for a crop at a given quality grade."""
    base = BENCHMARK.get(crop, 30)
    return round(base * GRADE_FACTOR.get(grade, 1.0), 2)


def farmer_payout(amount):
    """What the farmer receives after the platform + transport fees (87%)."""
    return round(amount * (1 - PLATFORM_FEE - TRANSPORT_FEE), 2)


def platform_cut(amount):
    """The platform fee portion of a sale."""
    return round(amount * PLATFORM_FEE, 2)


def transport_cut(amount):
    """The transport / logistics fee portion of a sale."""
    return round(amount * TRANSPORT_FEE, 2)


def traditional_farmer_share(amount):
    """What the farmer would have received in the old middleman chain."""
    return round(amount * TRAD_FARMER_SHARE, 2)


DELIVERY_FEE = 30.0        # flat delivery charge in Rupees
FREE_DELIVERY_ABOVE = 1000.0  # delivery is free for orders above this


def delivery_fee(items_total):
    """Flat delivery charge, waived for larger orders."""
    if items_total >= FREE_DELIVERY_ABOVE or items_total <= 0:
        return 0.0
    return DELIVERY_FEE


def retail_saving(amount):
    """How much less the shopper pays here vs the traditional retail chain."""
    return round(amount * RETAIL_MARKUP, 2)
