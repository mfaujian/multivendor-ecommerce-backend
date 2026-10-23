"""Pricing rules shared by the product API and the order engine."""
from decimal import Decimal


def unit_price_for(product, quantity):
    """Return the unit price for `quantity` units: the cheapest tier whose min_qty <= quantity.

    Falls back to the product's base price when no tier applies.
    """
    best = Decimal(str(product.price))
    best_min_qty = 0
    for tier in product.price_tiers:
        if tier.min_qty <= quantity and tier.min_qty > best_min_qty:
            best = Decimal(str(tier.unit_price))
            best_min_qty = tier.min_qty
    return best