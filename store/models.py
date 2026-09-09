import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    icon = models.CharField(
        max_length=50, blank=True,
        help_text="Bootstrap icon class, e.g. 'bi-egg-fried'"
    )
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:menu') + f'?category={self.slug}'


class FoodItem(models.Model):
    SPICE_CHOICES = [
        (0, 'Not Spicy'),
        (1, 'Mild'),
        (2, 'Medium'),
        (3, 'Hot'),
        (4, 'Extra Hot'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    discount_price = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True,
        help_text="Optional discounted price shown as a special offer"
    )
    image = models.ImageField(upload_to='food/', blank=True, null=True)
    image_url = models.URLField(
        blank=True,
        help_text="Optional external image URL, used only when no image file is uploaded"
    )
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    spice_level = models.PositiveSmallIntegerField(choices=SPICE_CHOICES, default=0)
    prep_time_minutes = models.PositiveIntegerField(default=20, help_text="Estimated prep time in minutes")
    calories = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_available']),
            models.Index(fields=['is_featured']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while FoodItem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:food_detail', args=[self.slug])

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        return self.image_url

    @property
    def current_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def has_discount(self):
        return bool(self.discount_price and self.discount_price < self.price)

    @property
    def discount_percent(self):
        if self.has_discount:
            return round((1 - (self.discount_price / self.price)) * 100)
        return 0

    @property
    def average_rating(self):
        agg = self.reviews.aggregate(avg=models.Avg('rating'))
        return round(agg['avg'] or 0, 1)

    @property
    def review_count(self):
        return self.reviews.count()


class Review(models.Model):
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('food_item', 'user')

    def __str__(self):
        return f"{self.user} rated {self.food_item} {self.rating}/5"


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='cart', blank=True, null=True
    )
    session_key = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart #{self.pk}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), Decimal('0.00'))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    special_instructions = models.CharField(max_length=255, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'food_item')

    def __str__(self):
        return f"{self.quantity} x {self.food_item.name}"

    @property
    def line_total(self):
        return self.food_item.current_price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('momo', 'Mobile Money'),
        ('card', 'Card Payment'),
    ]
    DELIVERY_CHOICES = [
        ('delivery', 'Home Delivery'),
        ('pickup', 'Self Pickup'),
    ]

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='orders', blank=True, null=True
    )
    full_name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    delivery_type = models.CharField(max_length=10, choices=DELIVERY_CHOICES, default='delivery')
    address = models.CharField(max_length=255, blank=True)
    region = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    landmark = models.CharField(max_length=150, blank=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cod')
    momo_network = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_paid = models.BooleanField(
        default=False,
        help_text="True once Paystack confirms a successful charge. Always False for cash on delivery until the order is fulfilled.",
    )
    payment_reference = models.CharField(
        max_length=100, blank=True, db_index=True,
        help_text="Paystack transaction reference used to verify this order's payment.",
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            import random
            import string
            from django.utils import timezone
            stamp = timezone.now().strftime('%y%m%d')
            # Loop instead of trusting one random draw — with only 4 digits
            # of randomness, two orders placed the same day could otherwise
            # collide and violate the `unique=True` constraint.
            for _ in range(20):
                rand = ''.join(random.choices(string.digits, k=4))
                candidate = f"FH{stamp}{rand}"
                if not Order.objects.filter(order_number=candidate).exists():
                    self.order_number = candidate
                    break
            else:
                # Astronomically unlikely, but fall back to something
                # guaranteed unique rather than silently failing.
                self.order_number = f"FH{stamp}{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:order_detail', args=[self.order_number])

    @property
    def status_progress(self):
        """Return percentage progress for the order-tracking bar."""
        steps = ['pending', 'confirmed', 'preparing', 'out_for_delivery', 'delivered']
        if self.status == 'cancelled':
            return 0
        try:
            idx = steps.index(self.status)
        except ValueError:
            idx = 0
        return int((idx / (len(steps) - 1)) * 100)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.SET_NULL, null=True)
    food_name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    special_instructions = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.food_name}"

    @property
    def line_total(self):
        price = self.unit_price or 0
        return price * (self.quantity or 0)

class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} — {self.name}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
