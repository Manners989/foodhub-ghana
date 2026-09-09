from django.contrib import admin

from .models import (Cart, CartItem, Category, ContactMessage, FoodItem,
                      NewsletterSubscriber, Order, OrderItem, Review)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'item_count')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order', 'name')

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ('user', 'rating', 'comment', 'created_at')
    can_delete = True


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'discount_price', 'is_available',
                     'is_featured', 'average_rating', 'created_at')
    list_filter = ('category', 'is_available', 'is_featured', 'is_vegetarian', 'spice_level')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_available', 'is_featured', 'price')
    inlines = [ReviewInline]
    fieldsets = (
        (None, {'fields': ('category', 'name', 'slug', 'description', 'image', 'image_url')}),
        ('Pricing', {'fields': ('price', 'discount_price')}),
        ('Attributes', {'fields': ('is_available', 'is_featured', 'is_vegetarian',
                                    'spice_level', 'prep_time_minutes', 'calories')}),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('food_item', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('food_item__name', 'user__username', 'comment')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('line_total',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'total_items', 'subtotal', 'updated_at')
    inlines = [CartItemInline]
    search_fields = ('user__username', 'session_key')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('food_item', 'food_name', 'unit_price', 'quantity', 'line_total')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'full_name', 'phone_number', 'status',
                     'payment_method', 'is_paid', 'delivery_type', 'total', 'created_at')
    list_filter = ('status', 'payment_method', 'is_paid', 'delivery_type', 'created_at')
    search_fields = ('order_number', 'full_name', 'phone_number', 'email', 'payment_reference')
    list_editable = ('status',)
    readonly_fields = ('order_number', 'subtotal', 'delivery_fee', 'total', 'is_paid',
                        'payment_reference', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read',)
    list_editable = ('is_read',)
    search_fields = ('name', 'email', 'subject', 'message')


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)


admin.site.site_header = 'FoodHub Ghana Administration'
admin.site.site_title = 'FoodHub Admin'
admin.site.index_title = 'Manage your restaurant'
