from .models import Category
from .cart import get_cart


def cart_context(request):
    cart = get_cart(request, create=False)
    if cart:
        return {
            'nav_cart_count': cart.total_items,
            'nav_cart_subtotal': cart.subtotal,
        }
    return {'nav_cart_count': 0, 'nav_cart_subtotal': 0}


def site_context(request):
    return {
        'nav_categories': Category.objects.all(),
        'site_name': 'FoodHub Ghana',
        'currency': 'GH₵',
    }
