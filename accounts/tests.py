from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Profile
from store.models import Category, FoodItem

User = get_user_model()


class RegistrationTests(TestCase):
    def valid_data(self, **overrides):
        data = dict(
            first_name='Ama', last_name='Boateng', username='ama_b',
            email='ama@example.com', phone_number='0244000111',
            password1='S0me-Str0ng-Pass!', password2='S0me-Str0ng-Pass!',
        )
        data.update(overrides)
        return data

    def test_registration_creates_user_and_logs_them_in(self):
        response = self.client.post(reverse('accounts:register'), self.valid_data())
        self.assertRedirects(response, reverse('store:home'))
        user = User.objects.get(username='ama_b')
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.email, 'ama@example.com')

    def test_registration_creates_a_profile_with_phone_number(self):
        self.client.post(reverse('accounts:register'), self.valid_data())
        profile = Profile.objects.get(user__username='ama_b')
        self.assertEqual(profile.phone_number, '0244000111')

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            reverse('accounts:register'),
            self.valid_data(password2='something-else'),
        )
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_already_authenticated_user_is_redirected_away_from_register(self):
        User.objects.create_user('existing', password='pw12345!')
        self.client.login(username='existing', password='pw12345!')
        response = self.client.get(reverse('accounts:register'))
        self.assertRedirects(response, reverse('store:home'))


class LoginCartMergeTests(TestCase):
    """Verifies a guest's session cart is folded into their account cart on login."""

    def setUp(self):
        self.user = User.objects.create_user('kojo', password='pw12345!')
        category = Category.objects.create(name='Drinks')
        self.item = FoodItem.objects.create(
            category=category, name='Sobolo', description='Hibiscus drink', price=Decimal('10.00'),
        )

    def test_session_cart_items_move_to_user_cart_on_login(self):
        # Add an item to the cart as an anonymous guest first.
        self.client.post(reverse('store:cart_add', args=[self.item.slug]), {'quantity': 2})

        # Now log in — the merge should carry the guest cart's items over.
        self.client.post(reverse('accounts:login'), {'username': 'kojo', 'password': 'pw12345!'})

        self.assertEqual(self.user.cart.items.count(), 1)
        self.assertEqual(self.user.cart.items.first().quantity, 2)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('adjoa', password='pw12345!')
        self.client.login(username='adjoa', password='pw12345!')

    def test_profile_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_profile_update_saves_both_forms(self):
        response = self.client.post(reverse('accounts:profile'), {
            'first_name': 'Adjoa', 'last_name': 'Osei', 'email': 'adjoa@example.com',
            'phone_number': '0201112222', 'address': '12 Ring Road', 'region': 'Greater Accra', 'city': 'Accra',
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Adjoa')
        self.assertEqual(self.user.profile.city, 'Accra')
