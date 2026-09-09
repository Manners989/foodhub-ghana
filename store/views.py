import hashlib
import hmac
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import payments
from .cart import get_cart
from .forms import CheckoutForm, ContactForm, NewsletterForm, ReviewForm
from .models import Category, FoodItem, Order, OrderItem, Review

logger = logging.getLogger(__name__)

DELIVERY_FEE = Decimal('15.00')
FREE_DELIVERY_THRESHOLD = Decimal('150.00')


@csrf_exempt
@require_POST
def paystack_webhook(request):
    secret = getattr(settings, 'PAYSTACK_SECRET_KEY', '').encode('utf-8')
    paystack_signature = request.headers.get('x-paystack-signature', '')

    computed_signature = hmac.new(secret, request.body, hashlib.sha512).hexdigest()

    if computed_signature != paystack_signature:
        logger.warning("Paystack webhook: invalid signature.")
        return HttpResponse(status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)

    event = payload.get('event')
    data = payload.get('data', {})

    if event == 'charge.success':
        reference = data.get('reference')
        if reference:
            try:
                order = Order.objects.get(payment_reference=reference)
                if not order.is_paid:
                    order.is_paid = True
                    order.status = 'confirmed'
                    order.save(update_fields=['is_paid', 'status'])
                    logger.info(f"Order {order.order_number} confirmed via webhook.")
            except Order.DoesNotExist:
                logger.error(f"Paystack webhook: order with reference {reference} not found.")

    return HttpResponse(status=200)


def home(request):
    categories = Category.objects.all()[:8]
    featured = FoodItem.objects.filter(is_available=True, is_featured=True)[:8]
    popular = (
        FoodItem.objects.filter(is_available=True)
        .order_by('-created_at')[:8]
    )
    newsletter_form = NewsletterForm()
    context = {
        'categories': categories,
        'featured': featured,
        'popular': popular,
        'newsletter_form': newsletter_form,
    }
    return render(request, 'store/home.html', context)


def menu(request):
    items = FoodItem.objects.filter(is_available=True).select_related('category')

    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '')
    sort = request.GET.get('sort', 'newest')
    veg_only = request.GET.get('veg') == '1'
    max_price = request.GET.get('max_price')

    if query:
        items = items.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_slug:
        items = items.filter(category__slug=category_slug)
    if veg_only:
        items = items.filter(is_vegetarian=True)
    if max_price:
        try:
            items = items.filter(price__lte=Decimal(max_price))
        except Exception:
            pass

    sort_map = {
        'newest': '-created_at',
        'price_low': 'price',
        'price_high': '-price',
        'name': 'name',
    }
    items = items.order_by(sort_map.get(sort, '-created_at'))

    paginator = Paginator(items, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'categories': Category.objects.all(),
        'query': query,
        'category_slug': category_slug,
        'sort': sort,
        'veg_only': veg_only,
        'max_price': max_price or '',
        'result_count': items.count(),
    }
    return render(request, 'store/menu.html', context)


def food_detail(request, slug):
    item = get_object_or_404(FoodItem.objects.select_related('category'), slug=slug, is_available=True)
    reviews = item.reviews.select_related('user')
    related = FoodItem.objects.filter(category=item.category, is_available=True).exclude(pk=item.pk)[:4]

    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()

    review_form = ReviewForm(instance=user_review)

    if request.method == 'POST' and request.user.is_authenticated:
        review_form = ReviewForm(request.POST, instance=user_review)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.food_item = item
            review.user = request.user
            review.save()
            messages.success(request, 'Thanks for your review!')
            return redirect('store:food_detail', slug=item.slug)

    context = {
        'item': item,
        'reviews': reviews,
        'related': related,
        'review_form': review_form,
        'user_review': user_review,
        'rating_range': range(1, 6),
    }
    return render(request, 'store/food_detail.html', context)


def _cart_payload(cart):
    return {
        'count': cart.total_items,
        'subtotal': f"{cart.subtotal:.2f}",
        'items': [
            {
                'id': ci.id,
                'name': ci.food_item.name,
                'quantity': ci.quantity,
                'unit_price': f"{ci.food_item.current_price:.2f}",
                'line_total': f"{ci.line_total:.2f}",
                'image': ci.food_item.display_image,
                'slug': ci.food_item.slug,
            }
            for ci in cart.items.select_related('food_item').all()
        ],
    }


@require_POST
def cart_add(request, slug):
    item = get_object_or_404(FoodItem, slug=slug, is_available=True)
    cart = get_cart(request, create=True)
    quantity = int(request.POST.get('quantity', 1) or 1)
    quantity = max(1, quantity)

    cart_item, created = cart.items.get_or_create(food_item=item, defaults={'quantity': quantity})
    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'cart': _cart_payload(cart), 'message': f'{item.name} added to cart.'})

    messages.success(request, f'{item.name} added to your cart.')
    return redirect(request.META.get('HTTP_REFERER', 'store:menu'))


@require_POST
def cart_update(request, item_id):
    cart = get_cart(request, create=True)
    cart_item = get_object_or_404(cart.items, id=item_id)
    quantity = int(request.POST.get('quantity', 1) or 1)

    if quantity <= 0:
        cart_item.delete()
    else:
        cart_item.quantity = quantity
        cart_item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'cart': _cart_payload(cart)})
    return redirect('store:cart_detail')


@require_POST
def cart_remove(request, item_id):
    cart = get_cart(request, create=True)
    cart_item = get_object_or_404(cart.items, id=item_id)
    cart_item.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'cart': _cart_payload(cart)})
    messages.info(request, 'Item removed from cart.')
    return redirect('store:cart_detail')


def cart_detail(request):
    cart = get_cart(request, create=True)
    delivery_fee = Decimal('0.00') if cart.subtotal >= FREE_DELIVERY_THRESHOLD or cart.subtotal == 0 else DELIVERY_FEE
    context = {
        'cart': cart,
        'delivery_fee': delivery_fee,
        'total': cart.subtotal + delivery_fee,
        'free_delivery_threshold': FREE_DELIVERY_THRESHOLD,
    }
    return render(request, 'store/cart.html', context)


def checkout(request):
    cart = get_cart(request, create=True)
    if cart.total_items == 0:
        messages.warning(request, 'Your cart is empty. Add something tasty first!')
        return redirect('store:menu')

    delivery_fee = Decimal('0.00') if cart.subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_FEE
    total = cart.subtotal + delivery_fee

    initial = {}
    if request.user.is_authenticated:
        initial = {'full_name': request.user.get_full_name() or request.user.username, 'email': request.user.email}

    if request.method == 'POST':
        form = CheckoutForm(request.POST, initial=initial)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user if request.user.is_authenticated else None
            order.subtotal = cart.subtotal
            order.delivery_fee = Decimal('0.00') if order.delivery_type == 'pickup' else delivery_fee
            order.total = order.subtotal + order.delivery_fee
            order.save()

            for cart_item in cart.items.select_related('food_item'):
                OrderItem.objects.create(
                    order=order,
                    food_item=cart_item.food_item,
                    food_name=cart_item.food_item.name,
                    unit_price=cart_item.food_item.current_price,
                    quantity=cart_item.quantity,
                    special_instructions=cart_item.special_instructions,
                )

            if order.payment_method == 'cod':
                cart.items.all().delete()
                messages.success(request, f'Order {order.order_number} placed successfully!')
                return redirect('store:order_success', order_number=order.order_number)

            order.payment_reference = order.order_number
            order.save(update_fields=['payment_reference'])
            try:
                authorization_url = payments.initialize_transaction(
                    email=order.email or 'guest@foodhub.gh',
                    amount_cedis=order.total,
                    reference=order.payment_reference,
                    callback_url=request.build_absolute_uri(reverse('store:payment_callback')),
                )
            except payments.PaystackError as exc:
                order.delete()
                messages.error(request, f'Could not start payment: {exc} Please try again or choose cash on delivery.')
                return redirect('store:checkout')

            return redirect(authorization_url)
    else:
        form = CheckoutForm(initial=initial)

    context = {
        'form': form,
        'cart': cart,
        'delivery_fee': delivery_fee,
        'total': total,
        'free_delivery_threshold': FREE_DELIVERY_THRESHOLD,
    }
    return render(request, 'store/checkout.html', context)


def payment_callback(request):
    reference = request.GET.get('reference') or request.GET.get('trxref')
    if not reference:
        messages.error(request, 'No payment reference was provided.')
        return redirect('store:menu')

    order = get_object_or_404(Order, payment_reference=reference)

    try:
        payments.verify_transaction(reference)
    except payments.PaystackError as exc:
        messages.error(
            request,
            f'Payment could not be confirmed: {exc} Your order has not been placed — please try again.',
        )
        order.delete()
        return redirect('store:checkout')

    order.is_paid = True
    order.status = 'confirmed'
    order.save(update_fields=['is_paid', 'status'])

    cart = get_cart(request, create=False)
    if cart:
        cart.items.all().delete()

    messages.success(request, f'Payment received — order {order.order_number} is confirmed!')
    return redirect('store:order_success', order_number=order.order_number)


def _can_view_order(request, order):
    if order.user_id is None:
        return True
    return request.user.is_authenticated and (request.user.pk == order.user_id or request.user.is_staff)


def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if not _can_view_order(request, order):
        raise Http404
    return render(request, 'store/order_success.html', {'order': order})


def order_tracking(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if not _can_view_order(request, order):
        raise Http404
    return render(request, 'store/order_detail.html', {'order': order})


@login_required
def order_history(request):
    orders = request.user.orders.all().prefetch_related('items')
    return render(request, 'store/order_history.html', {'orders': orders})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thanks for reaching out! We'll get back to you shortly.")
            return redirect('store:contact')
    else:
        form = ContactForm()
    return render(request, 'store/contact.html', {'form': form})


def about(request):
    return render(request, 'store/about.html')


@require_POST
def newsletter_signup(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        form.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': "You're subscribed!"})
        messages.success(request, "You're subscribed!")
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': 'Please enter a valid email.'}, status=400)
        messages.error(request, 'Please enter a valid email address.')
    return redirect(request.META.get('HTTP_REFERER', 'store:home'))