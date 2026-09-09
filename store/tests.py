"""
Tests for the store app.

Run with:  python manage.py test
Or with coverage:  coverage run manage.py test && coverage report
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Category, FoodItem, Order
from .payments import PaystackError

User = get_user_model()


def make_food_item(**overrides):
    category = overrides.pop('category', None) or Category.objects.create(name='Rice Dishes')
    defaults = dict(
        category=category,
        name='Jollof Rice',
        description='Smoky party jollof.',
        price=Decimal('45.00'),
    )
    defaults.update(overrides)
    return FoodItem.objects.create(**defaults)


class CategoryModelTests(TestCase):
    def test_slug_is_generated_from_name(self):
        category = Category.objects.create(name='Grilled & BBQ')
        self.assertEqual(category.slug, 'grilled-bbq')

    def test_explicit_slug_is_respected(self):
        category = Category.objects.create(name='Soups', slug='custom-slug')
        self.assertEqual(category.slug, 'custom-slug')


class FoodItemModelTests(TestCase):
    def test_duplicate_names_get_unique_slugs(self):
        item1 = make_food_item(name='Waakye')
        item2 = make_food_item(name='Waakye')
        self.assertEqual(item1.slug, 'waakye')
        self.assertEqual(item2.slug, 'waakye-2')

    def test_current_price_uses_discount_when_present(self):
        item = make_food_item(price=Decimal('50.00'), discount_price=Decimal('40.00'))
        self.assertEqual(item.current_price, Decimal('40.00'))

    def test_current_price_falls_back_to_regular_price(self):
        item = make_food_item(price=Decimal('50.00'))
        self.assertEqual(item.current_price, Decimal('50.00'))

    def test_has_discount_is_false_when_discount_is_not_lower(self):
        item = make_food_item(price=Decimal('50.00'), discount_price=Decimal('50.00'))
        self.assertFalse(item.has_discount)

    def test_discount_percent_rounds_correctly(self):
        item = make_food_item(price=Decimal('100.00'), discount_price=Decimal('75.00'))
        self.assertEqual(item.discount_percent, 25)

    def test_average_rating_with_no_reviews_is_zero(self):
        item = make_food_item()
        self.assertEqual(item.average_rating, 0)


class OrderModelTests(TestCase):
    def _build_order(self, **overrides):
        defaults = dict(full_name='Ama Mensah', phone_number='0244000000', total=Decimal('50.00'))
        defaults.update(overrides)
        return Order.objects.create(**defaults)

    def test_order_number_is_generated_on_save(self):
        order = self._build_order()
        self.assertTrue(order.order_number.startswith('FH'))
        self.assertEqual(len(order.order_number), 12)  # FH + 6-digit date + 4 random digits

    def test_order_number_is_not_regenerated_on_update(self):
        order = self._build_order()
        original_number = order.order_number
        order.status = 'confirmed'
        order.save()
        self.assertEqual(order.order_number, original_number)

    def test_order_numbers_are_unique_even_with_collisions(self):
        # Force the random generator to always return the same digits the
        # first two times, to prove the retry loop in Order.save() actually
        # avoids a collision instead of crashing on the unique constraint.
        with patch('random.choices', side_effect=[list('1234'), list('1234'), list('5678')]):
            order1 = self._build_order()
            order2 = self._build_order()
        self.assertNotEqual(order1.order_number, order2.order_number)

    def test_status_progress_for_cancelled_order_is_zero(self):
        order = self._build_order(status='cancelled')
        self.assertEqual(order.status_progress, 0)

    def test_status_progress_for_delivered_order_is_full(self):
        order = self._build_order(status='delivered')
        self.assertEqual(order.status_progress, 100)


class CartTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.item = make_food_item(price=Decimal('20.00'))

    def test_add_to_cart_creates_session_cart(self):
        response = self.client.post(
            reverse('store:cart_add', args=[self.item.slug]), {'quantity': 2},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['cart']['count'], 2)

    def test_adding_same_item_twice_increments_quantity_not_rows(self):
        url = reverse('store:cart_add', args=[self.item.slug])
        kwargs = dict(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.client.post(url, {'quantity': 1}, **kwargs)
        response = self.client.post(url, {'quantity': 1}, **kwargs)
        self.assertEqual(response.json()['cart']['count'], 2)

    def test_cart_totals_reflect_current_price(self):
        self.client.post(reverse('store:cart_add', args=[self.item.slug]), {'quantity': 3})
        response = self.client.get(reverse('store:cart_detail'))
        self.assertContains(response, '60.00')  # 3 x GH₵20.00


class CheckoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.item = make_food_item(price=Decimal('30.00'))
        self.client.post(reverse('store:cart_add', args=[self.item.slug]), {'quantity': 1})

    def valid_checkout_data(self, **overrides):
        data = dict(
            full_name='Kwame Owusu',
            phone_number='0244123456',
            email='kwame@example.com',
            delivery_type='pickup',
            payment_method='cod',
            momo_network='',
            notes='',
        )
        data.update(overrides)
        return data

    def test_cash_on_delivery_creates_order_and_empties_cart(self):
        response = self.client.post(reverse('store:checkout'), self.valid_checkout_data())
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.payment_method, 'cod')
        self.assertFalse(order.is_paid)
        self.assertRedirects(response, reverse('store:order_success', args=[order.order_number]))

    def test_delivery_without_address_is_rejected(self):
        response = self.client.post(
            reverse('store:checkout'),
            self.valid_checkout_data(delivery_type='delivery', address=''),
        )
        self.assertEqual(Order.objects.count(), 0)
        self.assertContains(response, 'Please provide a delivery address.')

    def test_momo_without_network_is_rejected(self):
        response = self.client.post(
            reverse('store:checkout'),
            self.valid_checkout_data(payment_method='momo', momo_network=''),
        )
        self.assertEqual(Order.objects.count(), 0)
        self.assertContains(response, 'Please select your Mobile Money network.')

    @patch('store.views.payments.initialize_transaction')
    def test_momo_checkout_redirects_to_paystack_and_keeps_order_unpaid(self, mock_init):
        mock_init.return_value = 'https://checkout.paystack.com/abc123'
        response = self.client.post(
            reverse('store:checkout'),
            self.valid_checkout_data(payment_method='momo', momo_network='MTN'),
        )
        self.assertRedirects(response, 'https://checkout.paystack.com/abc123', fetch_redirect_response=False)
        order = Order.objects.get()
        self.assertFalse(order.is_paid)
        self.assertTrue(order.payment_reference)
        mock_init.assert_called_once()

    @patch('store.views.payments.initialize_transaction')
    def test_paystack_failure_rolls_back_the_order(self, mock_init):
        mock_init.side_effect = PaystackError('network down')
        self.client.post(
            reverse('store:checkout'),
            self.valid_checkout_data(payment_method='card'),
        )
        self.assertEqual(Order.objects.count(), 0)


class PaymentCallbackTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.order = Order.objects.create(
            full_name='Efua Asante', phone_number='0201234567',
            total=Decimal('75.00'), payment_method='card',
        )
        self.order.payment_reference = self.order.order_number
        self.order.save(update_fields=['payment_reference'])

    @patch('store.views.payments.verify_transaction')
    def test_verified_payment_marks_order_paid(self, mock_verify):
        mock_verify.return_value = {'status': 'success'}
        response = self.client.get(
            reverse('store:payment_callback'), {'reference': self.order.payment_reference}
        )
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.status, 'confirmed')
        self.assertRedirects(response, reverse('store:order_success', args=[self.order.order_number]))

    @patch('store.views.payments.verify_transaction')
    def test_failed_verification_deletes_the_order(self, mock_verify):
        mock_verify.side_effect = PaystackError('payment was declined')
        self.client.get(reverse('store:payment_callback'), {'reference': self.order.payment_reference})
        self.assertFalse(Order.objects.filter(pk=self.order.pk).exists())

    def test_missing_reference_redirects_without_crashing(self):
        response = self.client.get(reverse('store:payment_callback'))
        self.assertRedirects(response, reverse('store:menu'))


class OrderAuthorizationTests(TestCase):
    """
    Guest orders (no account) stay viewable by order number, by design —
    that's how a customer without an account tracks their food. Orders tied
    to an account should only be visible to that account or staff.
    """

    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pw12345!')
        self.other_user = User.objects.create_user('rando', password='pw12345!')
        self.staff = User.objects.create_user('staffer', password='pw12345!', is_staff=True)
        self.guest_order = Order.objects.create(full_name='Guest', phone_number='000', total=Decimal('10.00'))
        self.owned_order = Order.objects.create(
            user=self.owner, full_name='Owner', phone_number='111', total=Decimal('10.00'),
        )

    def test_guest_order_is_viewable_by_anyone_with_the_number(self):
        response = self.client.get(reverse('store:order_detail', args=[self.guest_order.order_number]))
        self.assertEqual(response.status_code, 200)

    def test_owned_order_is_not_viewable_by_anonymous_visitor(self):
        response = self.client.get(reverse('store:order_detail', args=[self.owned_order.order_number]))
        self.assertEqual(response.status_code, 404)

    def test_owned_order_is_not_viewable_by_a_different_user(self):
        self.client.login(username='rando', password='pw12345!')
        response = self.client.get(reverse('store:order_detail', args=[self.owned_order.order_number]))
        self.assertEqual(response.status_code, 404)

    def test_owned_order_is_viewable_by_its_owner(self):
        self.client.login(username='owner', password='pw12345!')
        response = self.client.get(reverse('store:order_detail', args=[self.owned_order.order_number]))
        self.assertEqual(response.status_code, 200)

    def test_owned_order_is_viewable_by_staff(self):
        self.client.login(username='staffer', password='pw12345!')
        response = self.client.get(reverse('store:order_detail', args=[self.owned_order.order_number]))
        self.assertEqual(response.status_code, 200)


class MenuViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Rice Dishes')
        self.available = make_food_item(category=self.category, name='Jollof', is_available=True)
        self.unavailable = make_food_item(category=self.category, name='Sold Out Dish', is_available=False)

    def test_menu_only_shows_available_items(self):
        response = self.client.get(reverse('store:menu'))
        self.assertContains(response, 'Jollof')
        self.assertNotContains(response, 'Sold Out Dish')

    def test_menu_filters_by_max_price_and_ignores_bad_input(self):
        response = self.client.get(reverse('store:menu'), {'max_price': 'not-a-number'})
        self.assertEqual(response.status_code, 200)
