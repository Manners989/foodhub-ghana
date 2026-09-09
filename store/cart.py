"""
Small helper module to resolve the active Cart for a request.

Logged-in users get a Cart tied to their account. Anonymous visitors
get a Cart tied to their session key, so items persist across pages
without requiring an account, and can be merged into their account
cart once they log in (see accounts.signals).
"""
from .models import Cart


def get_cart(request, create=True):
    if request.user.is_authenticated:
        cart = getattr(request.user, 'cart', None)
        if cart is None and create:
            cart = Cart.objects.create(user=request.user)
        return cart

    if not request.session.session_key:
        if not create:
            return None
        request.session.create()

    session_key = request.session.session_key
    cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    if cart is None and create:
        cart = Cart.objects.create(session_key=session_key)
    return cart


def merge_session_cart_into_user(request, user):
    """Called on login to fold an anonymous cart into the user's cart."""
    session_key = request.session.session_key
    if not session_key:
        return
    session_cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    if not session_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)
    for item in session_cart.items.all():
        existing = user_cart.items.filter(food_item=item.food_item).first()
        if existing:
            existing.quantity += item.quantity
            existing.save()
        else:
            item.cart = user_cart
            item.save()
    session_cart.delete()
